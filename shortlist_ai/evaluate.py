"""Ranking evaluation against hand-graded relevance labels.

Layout (see eval/):
    eval/jobs/<job>.md            job descriptions
    eval/resumes/*                candidate resumes (synthetic)
    eval/labels.json              {"<job>": {"<resume stem>": grade}}

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
from .extract import Cache, extract_job
from .pipeline import Ranking, rank


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


def run_eval(eval_dir: Path, backend: Backend, cache: Cache, progress=None) -> list[JobEval]:
    labels = json.loads((eval_dir / "labels.json").read_text())
    resumes = sorted(p for p in (eval_dir / "resumes").iterdir() if not p.name.startswith("."))
    out = []
    for job_name, grades in labels.items():
        job = extract_job(eval_dir / "jobs" / f"{job_name}.md", backend, cache)
        # Evaluate the ranking stage itself: no prefilter cut.
        ranking = rank(job, resumes, backend, cache=cache, prefilter_k=len(resumes), progress=progress)
        # Failed candidates go to the bottom, so failures cost ranking quality.
        order = [r.candidate_id for r in ranking.results] + sorted(ranking.errors)
        out.append(JobEval(job_name, ranking, [grades.get(c, 0) for c in order],
                           [grades.get(p.stem, 0) for p in resumes]))
    return out


def eval_report(evals: list[JobEval], backend_desc: str) -> str:
    out = [f"# Ranking eval: `{backend_desc}`", "",
           "| Job | NDCG@3 | NDCG@5 | P@3 | Top-1 correct |", "|---|---|---|---|---|"]
    for e in evals:
        m = e.metrics()
        out.append(f"| {e.job} | {m['ndcg@3']:.2f} | {m['ndcg@5']:.2f} | {m['p@3']:.2f} | "
                   f"{'yes' if m['top1'] else 'no'} |")
    if evals:
        avg = {k: sum(e.metrics()[k] for e in evals) / len(evals) for k in evals[0].metrics()}
        out.append(f"| **mean** | **{avg['ndcg@3']:.2f}** | **{avg['ndcg@5']:.2f}** | "
                   f"**{avg['p@3']:.2f}** | **{avg['top1']:.0%}** |")
    for e in evals:
        out += ["", f"## {e.job}", "", "| Rank | Candidate | Score | Gold grade |", "|---|---|---|---|"]
        for i, (r, g) in enumerate(zip(e.ranking.results, e.ranked_grades), 1):
            out.append(f"| {i} | {r.candidate_id} | {r.score:.0f} | {g} |")
        for cid, err in e.ranking.errors.items():
            out.append(f"| - | {cid} | failed: {err[:60]} | - |")
    return "\n".join(out) + "\n"
