"""Stage 3: judge each requirement with the LLM, then compute the score in code.

The model only makes per-requirement judgments (met / partial / not_met) and must
quote its evidence verbatim from the blind profile. Everything numeric happens
here, deterministically, so scores are auditable and weights are adjustable:

  score = 100 * sum(weight * credit) / sum(weight)
  weight: must_have 3, nice_to_have 1      credit: met 1, partial 0.5, not_met 0

A core must-have (the role's central skill, marked by the extractor) caps the score when it isn't
met, because the weights alone let a candidate miss the job's whole point and still score well:

  core not_met: score at most 40      core partial: 65, plus a quarter of what it scored above 65

The partial cap is soft so that capped jobs keep their order instead of all tying at 65; a job with a
core partial still can't pass 73.75. The cap is recorded in the result's flags.

Evidence that can't be found in the profile is treated as hallucinated: the
verdict is downgraded one level and the candidate is flagged for review, with the
quote that wasn't found. Entries that only echo the requirement or note an absence
are set aside (and flagged) first, since they claim nothing about the candidate.
The core cap follows the model's own verdict, not the downgraded one: a quote that
is only slightly off (small models paraphrase) costs that requirement's credit, but
doesn't cap a candidate who has the job's central skill.

"N+ years of X" requirements are computed in code from role durations; see years.py.
"""

import random
import re
from collections.abc import Mapping

from .backends import Backend, Deferred
from .blind import Role
from .evidence import _norm, quote_in_profile
from .prompts import SCORE_SYSTEM as SCORE_SYSTEM  # the prompts live in prompts.py; still importable from here
from .prompts import resolve
from .schema import CandidateAssessment, CandidateResult, JobSpec, RequirementAssessment, ScoredRequirement
from .years import assess_years, min_years

WEIGHTS = {"must_have": 3.0, "nice_to_have": 1.0}
CREDIT = {"met": 1.0, "partial": 0.5, "not_met": 0.0}
CORE_CAP = {"not_met": 40.0, "partial": 65.0}  # where a core must-have with this verdict caps the score
ABOVE_CAP = {"not_met": 0.0, "partial": 0.25}  # the share of the score above the cap that's kept
DOWNGRADE = {"met": "partial", "partial": "not_met", "not_met": "not_met"}


_ABSENCE = re.compile(r"\b(?:is|are)\s+not\s+(?:mentioned|listed|shown|stated|present|found)\b"
                      r"|\bno\s+(?:mention|evidence)\s+of\b", re.I)


def is_non_quote(entry: str, requirement: str) -> bool:
    """An evidence entry that doesn't claim anything about the candidate: the requirement's own
    wording echoed back ("Practical experience using LLM APIs"), or a note that something is
    missing ("Splunk is not mentioned"). Small models put these in `evidence` despite the rules.
    They are set aside, not treated as hallucinated quotes. Only called on entries that failed
    quote_in_profile, so a real quote that happens to share the requirement's words still counts."""
    norm = _norm(entry)
    return bool(norm) and (norm in _norm(requirement) or bool(_ABSENCE.search(entry)))


def shuffle_requirements(job: JobSpec, seed: int) -> JobSpec:
    """The same job with its requirements in a seeded random order. Scoring looks requirements
    up by id, so only the model's input changes: a cheap way to measure its sensitivity."""
    requirements = list(job.requirements)
    random.Random(seed).shuffle(requirements)
    return job.model_copy(update={"requirements": requirements})


def build_prompt(job: JobSpec, profile: str, prompts: Mapping[str, str] | None = None) -> list[dict]:
    reqs = "\n".join(f"- id={r.id} [{r.kind}]: {r.description}" for r in job.requirements)
    text = resolve(prompts)["score_request"].format(title=job.title, requirements=reqs, profile=profile)
    return [{"type": "text", "text": text}]


def finalize(candidate_id: str, source_file: str, job: JobSpec, profile: str,
             assessment: CandidateAssessment) -> CandidateResult:
    """Turn the model's judgments into a verified, scored result."""
    by_id: dict[str, RequirementAssessment] = {}
    for a in assessment.assessments:
        by_id.setdefault(a.requirement_id, a)  # keep the first if the model repeats an id

    flags, scored, judged = [], [], {}  # judged: the model's own verdicts, for the core cap
    for req in job.requirements:
        a = by_id.get(req.id)
        if a is None:
            flags.append(f"no assessment returned for '{req.id}' (scored as not_met)")
            a = RequirementAssessment(requirement_id=req.id, verdict="not_met", evidence=[],
                                      reasoning="No assessment returned by the model.")
        ignored = [q for q in a.evidence
                   if not quote_in_profile(q, profile) and is_non_quote(q, req.description)]
        if ignored:
            a = a.model_copy(update={"evidence": [q for q in a.evidence if q not in ignored]})
            flags.append(f"'{req.id}': ignored {len(ignored)} evidence entr{'y' if len(ignored) == 1 else 'ies'} "
                         f"that quote the requirement or note an absence, not the profile")
        unverified = [q for q in a.evidence if not quote_in_profile(q, profile)]
        verified = not unverified
        verdict = judged[req.id] = a.verdict
        if a.verdict != "not_met" and not a.evidence:
            verified = False
        if not verified and verdict != "not_met":
            verdict = DOWNGRADE[verdict]
            missing = "no quote given" if not unverified else "; ".join(
                f"“{q[:80]}{'…' if len(q) > 80 else ''}”" for q in unverified)
            flags.append(f"'{req.id}': evidence not found in profile ({missing}); downgraded {a.verdict} -> {verdict}")
        scored.append(ScoredRequirement(**{**a.model_dump(), "verdict": verdict},
                                        kind=req.kind, core=req.core, evidence_verified=verified,
                                        unverified_quotes=unverified, ignored_evidence=ignored))

    total = sum(WEIGHTS[r.kind] for r in scored)
    earned = sum(WEIGHTS[r.kind] * CREDIT[r.verdict] for r in scored)
    musts = [r for r in scored if r.kind == "must_have"]
    unmet = [r.requirement_id for r in musts if r.verdict == "not_met"]
    if unmet:
        flags.append(f"missing must-have: {', '.join(unmet)}")
    score = round(100 * earned / total, 1) if total else 0.0
    for r in musts:
        verdict = judged[r.requirement_id]
        cap = CORE_CAP.get(verdict) if r.core else None
        if cap is not None and score > cap:
            capped = round(cap + (score - cap) * ABOVE_CAP[verdict], 1)
            flags.append(f"core requirement '{r.requirement_id}' {verdict.replace('_', ' ')}: "
                         f"score capped at {capped:g} (was {score})")
            score = capped
    return CandidateResult(
        candidate_id=candidate_id,
        source_file=source_file,
        score=score,
        must_haves_met=sum(1 for r in musts if r.verdict == "met"),
        must_haves_total=len(musts),
        requirements=scored,
        summary=assessment.summary,
        flags=flags,
    )


def score_candidate(candidate_id: str, source_file: str, job: JobSpec, profile: str,
                    backend: Backend, roles: list[Role] | None = None,
                    prompts: Mapping[str, str] | None = None) -> CandidateResult:
    """With `roles` (the profile's roles), "N+ years of X" verdicts are computed in code.
    prompts: {name: text} in place of the defaults (see prompts.py)."""
    prompts = resolve(prompts)
    years = ({r.id: (r, n) for r in job.requirements if (n := min_years(r.description)) is not None}
             if roles is not None else {})
    assessment, *computed = _every([
        lambda: backend.structured(prompts["score_system"], build_prompt(job, profile, prompts), CandidateAssessment),
        *(lambda r=r, n=n: assess_years(r, n, roles, backend, prompts) for r, n in years.values())])
    if roles is not None:
        assessment.assessments = [a for a in assessment.assessments if a.requirement_id not in years] + computed
    return finalize(candidate_id, source_file, job, profile, assessment)


def _every(calls: list) -> list:
    """Each call's result. The calls don't depend on each other, so one waiting for a batch (Deferred) doesn't
    stop the rest: a batch round queues them all, rather than one round each. Any other error stops at once."""
    results, waiting = [], None
    for call in calls:
        try:
            results.append(call())
        except Deferred as e:
            waiting = waiting or e
    if waiting:
        raise waiting
    return results
