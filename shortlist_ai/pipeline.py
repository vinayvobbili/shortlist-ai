"""End-to-end: resumes + job -> ranked, evidence-backed shortlist."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from .backends import Backend
from .blind import blind_profile
from .extract import Cache, extract_resume
from .prefilter import bm25_rank
from .schema import CandidateResult, JobSpec, Resume
from .score import score_candidate


@dataclass
class Ranking:
    job: JobSpec
    results: list[CandidateResult]                               # scored, best first
    not_assessed: list[str] = field(default_factory=list)       # below the prefilter cut
    errors: dict[str, str] = field(default_factory=dict)        # candidate -> error message


def profile_for(resume: Resume, blind: bool = True) -> str:
    """Blind by default. Unblinded mode exists only to measure what blinding prevents."""
    profile = blind_profile(resume)
    return profile if blind else f"Name: {resume.full_name}\n{profile}"


def rank(job: JobSpec, resume_paths: list[Path], backend: Backend, *, cache: Cache | None = None,
         prefilter_k: int = 25, blind: bool = True, workers: int = 1, progress=None) -> Ranking:
    progress = progress or (lambda msg: None)
    errors: dict[str, str] = {}

    # Stage 1: extraction (cached per file).
    profiles: dict[str, tuple[Path, str]] = {}
    extraction_flags: dict[str, list[str]] = {}
    for path in resume_paths:
        candidate_id = path.stem
        try:
            progress(f"extract  {candidate_id}")
            extracted = extract_resume(path, backend, cache)
            profiles[candidate_id] = (path, profile_for(extracted.resume, blind))
            extraction_flags[candidate_id] = extracted.flags
        except Exception as e:  # one bad file shouldn't sink the whole run
            errors[candidate_id] = f"{type(e).__name__}: {e}"

    # Stage 2: cheap prefilter for big pools.
    not_assessed: list[str] = []
    if len(profiles) > prefilter_k:
        query = " ".join(r.description for r in job.requirements)
        ordered = [cid for cid, _ in bm25_rank(query, {cid: p for cid, (_, p) in profiles.items()})]
        not_assessed = ordered[prefilter_k:]
        profiles = {cid: profiles[cid] for cid in ordered[:prefilter_k]}

    # Stage 3: LLM judgments + deterministic scoring.
    def work(item):
        candidate_id, (path, profile) = item
        progress(f"score    {candidate_id}")
        try:
            result = score_candidate(candidate_id, path.name, job, profile, backend)
            result.flags = extraction_flags[candidate_id] + result.flags
            return result
        except Exception as e:
            errors[candidate_id] = f"{type(e).__name__}: {e}"
            return None

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = [r for r in pool.map(work, profiles.items()) if r is not None]

    results.sort(key=lambda r: (-r.score, -r.must_haves_met, r.candidate_id))
    return Ranking(job, results, not_assessed, errors)


def job_order(job_id: str, result: CandidateResult) -> tuple:
    """Sort key for jobs, best fit first. Must-haves compared as a share: jobs list different numbers."""
    return (-result.score, -result.must_haves_met / max(1, result.must_haves_total), job_id)


@dataclass
class JobMatch:
    job_id: str
    job: JobSpec
    result: CandidateResult

    @property
    def gaps(self) -> list[str]:
        """Must-haves not met, as the job describes them: what a candidate would need to close."""
        return [next(r.description for r in self.job.requirements if r.id == s.requirement_id)
                for s in self.result.requirements if s.kind == "must_have" and s.verdict != "met"]


@dataclass
class JobMatches:
    resume_file: str
    matches: list[JobMatch]                                      # best fit first
    errors: dict[str, str] = field(default_factory=dict)        # job -> error message
    flags: list[str] = field(default_factory=list)              # about the resume itself


def match_jobs(resume_path: Path, jobs: dict[str, JobSpec], backend: Backend, *, cache: Cache | None = None,
               workers: int = 1, progress=None) -> JobMatches:
    """The reverse of rank(): one resume, many jobs, best fit first.

    Uses the same blind profile and scorer as rank(), so a (resume, job) score means the same
    thing in both directions. Scores are comparable across jobs because each is the weighted
    share of that job's requirements met; ties go to the job with more must-haves met.
    """
    progress = progress or (lambda msg: None)
    progress(f"extract  {resume_path.stem}")
    extracted = extract_resume(resume_path, backend, cache)
    profile = profile_for(extracted.resume)
    errors: dict[str, str] = {}

    def work(item):
        job_id, job = item
        progress(f"score    {job_id}")
        try:
            return JobMatch(job_id, job, score_candidate(resume_path.stem, resume_path.name, job, profile, backend))
        except Exception as e:
            errors[job_id] = f"{type(e).__name__}: {e}"
            return None

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        matches = [m for m in pool.map(work, jobs.items()) if m is not None]

    matches.sort(key=lambda m: job_order(m.job_id, m.result))
    return JobMatches(resume_path.name, matches, errors, extracted.flags)
