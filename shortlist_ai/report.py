"""Render a ranking as a reviewer-facing markdown report or JSON."""

import json

from .pipeline import JobMatches, Ranking

VERDICT_MARK = {"met": "✅ met", "partial": "🟡 partial", "not_met": "❌ not met"}

DISCLAIMER = (
    "> **Decision support, not a decision.** Scores are computed from per-requirement "
    "judgments made by an LLM on anonymized profiles. Check the evidence before acting "
    "on any result, and never reject a candidate on the score alone."
)


def _evidence_table(result) -> list[str]:
    out = ["| Requirement | Verdict | Evidence |", "|---|---|---|"]
    for req in result.requirements:
        evidence = "<br>".join(f"“{q}”" for q in req.evidence) or "—"
        if req.evidence and not req.evidence_verified:
            evidence += "<br>⚠️ not found in profile"
        out.append(f"| `{req.requirement_id}` | {VERDICT_MARK[req.verdict]} | {evidence} |")
    return out


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
        out += _evidence_table(r)
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


def jobs_to_markdown(matches: JobMatches, top: int, backend_desc: str) -> str:
    out = [f"# Job matches: {matches.resume_file}", "",
           "> Fit is judged per requirement from what the resume says. A gap can mean the experience "
           "is missing from the resume rather than from you: if you have it, say so in the resume.", "",
           f"Scored by `{backend_desc}` · {len(matches.matches)} jobs"
           + (f" · {len(matches.errors)} failed" if matches.errors else ""), ""]
    if matches.flags:
        out += ["**Notes about the resume:**"] + [f"- {f}" for f in matches.flags] + [""]

    out += ["## Ranking", "", "| # | Job | Fit | Must-haves | Gaps (must-haves not fully met) |", "|---|---|---|---|---|"]
    for i, m in enumerate(matches.matches, 1):
        r = m.result
        out.append(f"| {i} | {m.job.title} (`{m.job_id}`) | {r.score:.0f} | {r.must_haves_met}/{r.must_haves_total} | "
                   f"{'; '.join(m.gaps) or '—'} |")

    for i, m in enumerate(matches.matches[:top], 1):
        out += ["", f"## {i}. {m.job.title} — {m.result.score:.0f}/100", "", f"_{m.result.summary}_", ""]
        out += _evidence_table(m.result)
    if matches.errors:
        out += ["", "## Failed to process", ""] + [f"- **{j}**: {err}" for j, err in matches.errors.items()]
    return "\n".join(out) + "\n"


def jobs_to_json(matches: JobMatches) -> str:
    return json.dumps({
        "resume": matches.resume_file,
        "flags": matches.flags,
        "matches": [{"job_id": m.job_id, "job": m.job.model_dump(), "gaps": m.gaps, **m.result.model_dump()}
                    for m in matches.matches],
        "errors": matches.errors,
    }, indent=2, ensure_ascii=False)
