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
