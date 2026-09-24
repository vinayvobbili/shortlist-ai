"""Render a ranking as a reviewer-facing markdown report or JSON."""

import json

from .pipeline import Ranking

VERDICT_MARK = {"met": "✅ met", "partial": "🟡 partial", "not_met": "❌ not met"}

DISCLAIMER = (
    "> **Decision support, not a decision.** Scores are computed from per-requirement "
    "judgments made by an LLM on anonymized profiles. Check the evidence before acting "
    "on any result, and never reject a candidate on the score alone."
)


def to_markdown(ranking: Ranking, top: int, backend_desc: str) -> str:
    job = ranking.job
    out = [f"# Shortlist: {job.title}", "", DISCLAIMER, "",
           f"Scored by `{backend_desc}` · {len(ranking.results)} assessed"
           + (f" · {len(ranking.not_assessed)} below prefilter cut" if ranking.not_assessed else "")
           + (f" · {len(ranking.errors)} failed" if ranking.errors else ""), ""]

    out += ["## Requirements", "", "| id | type | requirement |", "|---|---|---|"]
    out += [f"| `{r.id}` | {r.kind.replace('_', '-')} | {r.description} |" for r in job.requirements]

    out += ["", "## Ranking", "", "| # | Candidate | Score | Must-haves | Flags |", "|---|---|---|---|---|"]
    for i, r in enumerate(ranking.results, 1):
        flags = "⚠️ " + str(len(r.flags)) if r.flags else ""
        out.append(f"| {i} | {r.candidate_id} | {r.score:.0f} | {r.must_haves_met}/{r.must_haves_total} | {flags} |")

    for i, r in enumerate(ranking.results[:top], 1):
        out += ["", f"## {i}. {r.candidate_id} — {r.score:.0f}/100", "", f"_{r.summary}_", ""]
        out += ["| Requirement | Verdict | Evidence |", "|---|---|---|"]
        for req in r.requirements:
            evidence = "<br>".join(f"“{q}”" for q in req.evidence) or "—"
            if req.evidence and not req.evidence_verified:
                evidence += "<br>⚠️ not found in profile"
            out.append(f"| `{req.requirement_id}` | {VERDICT_MARK[req.verdict]} | {evidence} |")
        if r.flags:
            out += ["", "**Review flags:**"] + [f"- {f}" for f in r.flags]

    if ranking.not_assessed:
        out += ["", "## Not assessed (below keyword prefilter cut)", "",
                "These were not scored, not rejected. Raise `--prefilter-k` to include them.", "",
                ", ".join(ranking.not_assessed)]
    if ranking.errors:
        out += ["", "## Failed to process", ""] + [f"- **{cid}**: {err}" for cid, err in ranking.errors.items()]
    return "\n".join(out) + "\n"


def to_json(ranking: Ranking) -> str:
    return json.dumps({
        "job": ranking.job.model_dump(),
        "results": [r.model_dump() for r in ranking.results],
        "not_assessed": ranking.not_assessed,
        "errors": ranking.errors,
    }, indent=2, ensure_ascii=False)
