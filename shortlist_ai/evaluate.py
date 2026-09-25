"""Ranking evaluation against hand-graded relevance labels, in both directions.

Layout (see eval/):
    eval/jobs/<job>.md            job descriptions
    eval/resumes/*                candidate resumes (synthetic)
    eval/labels.json              {"<job>": {"<resume stem>": grade}}
    eval/verdicts.json            optional: {"<job>": {"<resume>": {"<requirement id>": verdict}}}

A job can also be a reviewed requirements file, jobs/<job>.json, which fixes its
requirement ids so that verdicts.json can refer to them.

Every (job, resume) pair is scored once. Read per job, the scores rank candidates
(`shortlist rank`); read per resume, they rank jobs (`shortlist jobs`).

Grades: 3 strong fit, 2 good fit, 1 weak fit, 0 not a fit. Metrics:
    NDCG@k     ranking quality with graded relevance (1.0 = ideal order)
    P@k        share of the top k with grade >= 2
    top-1      whether the #1 pick has the highest grade available
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path

from .backends import Backend
from .extract import Cache, extract_job, load_job_spec
from .pipeline import Ranking, job_order, rank


def dcg(grades: list[int]) -> float:
    return sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(grades))


def ndcg_at_k(ranked_grades: list[int], all_grades: list[int], k: int) -> float:
    ideal = dcg(sorted(all_grades, reverse=True)[:k])
    return dcg(ranked_grades[:k]) / ideal if ideal else 1.0


def precision_at_k(ranked_grades: list[int], k: int, relevant: int = 2) -> float:
    top = ranked_grades[:k]
    return sum(1 for g in top if g >= relevant) / len(top) if top else 0.0


@dataclass
class JobEval:
    job: str
    ranking: Ranking
    ranked_grades: list[int]
    all_grades: list[int]

    def metrics(self) -> dict[str, float]:
        return {
            "ndcg@3": ndcg_at_k(self.ranked_grades, self.all_grades, 3),
            "ndcg@5": ndcg_at_k(self.ranked_grades, self.all_grades, 5),
            "p@3": precision_at_k(self.ranked_grades, 3),
            "top1": float(bool(self.ranked_grades) and self.ranked_grades[0] == max(self.all_grades)),
        }


@dataclass
class ResumeEval:
    resume: str
    ranked_jobs: list[tuple[str, float]]    # (job, score), best fit first
    grades: dict[str, int]                  # job -> gold grade

    @property
    def ranked_grades(self) -> list[int]:
        return [self.grades[j] for j, _ in self.ranked_jobs]

    def metrics(self) -> dict[str, float]:
        all_grades = list(self.grades.values())
        return {"ndcg@3": ndcg_at_k(self.ranked_grades, all_grades, 3),
                "top1": float(self.ranked_grades[0] == max(all_grades))}


def run_eval(eval_dir: Path, backend: Backend, cache: Cache, progress=None) -> tuple[list[JobEval], list[ResumeEval]]:
    labels = json.loads((eval_dir / "labels.json").read_text())
    resumes = sorted(p for p in (eval_dir / "resumes").iterdir() if not p.name.startswith("."))
    job_evals = []
    for job_name, grades in labels.items():
        reviewed = eval_dir / "jobs" / f"{job_name}.json"
        job = (load_job_spec(reviewed) if reviewed.exists()
               else extract_job(eval_dir / "jobs" / f"{job_name}.md", backend, cache))
        # Evaluate the ranking stage itself: no prefilter cut.
        ranking = rank(job, resumes, backend, cache=cache, prefilter_k=len(resumes), progress=progress)
        # Failed candidates go to the bottom, so failures cost ranking quality.
        order = [r.candidate_id for r in ranking.results] + sorted(ranking.errors)
        job_evals.append(JobEval(job_name, ranking, [grades.get(c, 0) for c in order],
                                 [grades.get(p.stem, 0) for p in resumes]))
    return job_evals, resume_evals(job_evals, labels)


def resume_evals(job_evals: list[JobEval], labels: dict) -> list[ResumeEval]:
    """Read the score matrix per resume. Only resumes that fit at least one job are evaluated,
    and a resume that failed to process is skipped (the job-direction metrics already count it)."""
    by_resume: dict[str, list] = {}
    for e in job_evals:
        for r in e.ranking.results:
            by_resume.setdefault(r.candidate_id, []).append((e.job, r))
    out = []
    for resume, pairs in sorted(by_resume.items()):
        grades = {job: labels[job].get(resume, 0) for job, _ in pairs}
        if max(grades.values()) == 0:
            continue
        pairs.sort(key=lambda p: job_order(p[0], p[1]))
        out.append(ResumeEval(resume, [(job, r.score) for job, r in pairs], grades))
    return out


VERDICT_RANK = {"not_met": 0, "partial": 1, "met": 2}


@dataclass
class VerdictCheck:
    job: str
    resume: str
    requirement: str
    expected: str
    got: str | None     # None: the candidate failed to process

    @property
    def outcome(self) -> str:
        if self.got == self.expected:
            return "agree"
        if self.got is None:
            return "missing"
        return "too lenient" if VERDICT_RANK[self.got] > VERDICT_RANK[self.expected] else "too strict"


def check_verdicts(job_evals: list[JobEval], expected: dict) -> list[VerdictCheck]:
    got = {(e.job, r.candidate_id, s.requirement_id): s.verdict
           for e in job_evals for r in e.ranking.results for s in r.requirements}
    return [VerdictCheck(job, resume, req, verdict, got.get((job, resume, req)))
            for job, by_resume in expected.items()
            for resume, by_req in by_resume.items()
            for req, verdict in by_req.items()]


def eval_report(evals: list[JobEval], resume_evals_: list[ResumeEval], backend_desc: str,
                verdicts: list[VerdictCheck] | None = None) -> str:
    out = [f"# Ranking eval: `{backend_desc}`", "",
           "## Candidates for each job (`shortlist rank`)", "",
           "| Job | NDCG@3 | NDCG@5 | P@3 | Top-1 correct |", "|---|---|---|---|---|"]
    for e in evals:
        m = e.metrics()
        out.append(f"| {e.job} | {m['ndcg@3']:.2f} | {m['ndcg@5']:.2f} | {m['p@3']:.2f} | "
                   f"{'yes' if m['top1'] else 'no'} |")
    if evals:
        avg = {k: sum(e.metrics()[k] for e in evals) / len(evals) for k in evals[0].metrics()}
        out.append(f"| **mean** | **{avg['ndcg@3']:.2f}** | **{avg['ndcg@5']:.2f}** | "
                   f"**{avg['p@3']:.2f}** | **{avg['top1']:.0%}** |")
    if resume_evals_:
        out += ["", "## Jobs for each resume (`shortlist jobs`)", "",
                f"Resumes that fit at least one of the {len(evals)} jobs.", "",
                "| Resume | Top pick (grade) | Best grade available | NDCG@3 |", "|---|---|---|---|"]
        for r in resume_evals_:
            top_job, top_score = r.ranked_jobs[0]
            out.append(f"| {r.resume} | {top_job} ({r.grades[top_job]}, score {top_score:.0f}) | "
                       f"{max(r.grades.values())} | {r.metrics()['ndcg@3']:.2f} |")
        n = len(resume_evals_)
        out.append(f"| **mean** | **top-1 correct: {sum(r.metrics()['top1'] for r in resume_evals_) / n:.0%}** | | "
                   f"**{sum(r.metrics()['ndcg@3'] for r in resume_evals_) / n:.2f}** |")
    if verdicts:
        counts = {k: sum(v.outcome == k for v in verdicts) for k in ("agree", "too lenient", "too strict", "missing")}
        out += ["", "## Requirement verdicts vs. expected", "",
                f"**{counts['agree']}/{len(verdicts)} agree** · {counts['too lenient']} too lenient · "
                f"{counts['too strict']} too strict" + (f" · {counts['missing']} missing" if counts["missing"] else "")]
        wrong = [v for v in verdicts if v.outcome != "agree"]
        if wrong:
            out += ["", "| Job | Candidate | Requirement | Expected | Got | |", "|---|---|---|---|---|---|"]
            out += [f"| {v.job} | {v.resume} | `{v.requirement}` | {v.expected} | {v.got or '—'} | {v.outcome} |"
                    for v in wrong]
    out += ["", "## Per-job rankings"]
    for e in evals:
        out += ["", f"### {e.job}", "", "| Rank | Candidate | Score | Gold grade |", "|---|---|---|---|"]
        for i, (r, g) in enumerate(zip(e.ranking.results, e.ranked_grades, strict=False), 1):
            out.append(f"| {i} | {r.candidate_id} | {r.score:.0f} | {g} |")
        for cid, err in e.ranking.errors.items():
            out.append(f"| - | {cid} | failed: {err[:60]} | - |")
    return "\n".join(out) + "\n"
