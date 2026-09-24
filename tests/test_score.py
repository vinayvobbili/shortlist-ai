from shortlist_ai.schema import CandidateAssessment, JobSpec, Requirement, RequirementAssessment
from shortlist_ai.score import finalize, quote_in_profile

PROFILE = """CANDIDATE PROFILE
- Senior Security Engineer at Northwind Health (4 yrs, current role)
  * Built SOAR playbooks in Python that cut triage time by 60%
Skills: Python, Splunk"""

JOB = JobSpec(title="IR Engineer", requirements=[
    Requirement(id="python", description="Python scripting", kind="must_have"),
    Requirement(id="siem", description="SIEM experience", kind="must_have"),
    Requirement(id="soar", description="SOAR playbooks", kind="nice_to_have"),
])


def a(rid, verdict, evidence=(), reasoning="r"):
    return RequirementAssessment(requirement_id=rid, verdict=verdict, evidence=list(evidence), reasoning=reasoning)


def test_quote_matching():
    assert quote_in_profile("built SOAR playbooks in Python", PROFILE)
    assert quote_in_profile("Built SOAR playbooks ... cut triage time by 60%", PROFILE)
    assert quote_in_profile("Skills:  python,   splunk", PROFILE)
    assert not quote_in_profile("Led a team of 12 engineers", PROFILE)
    assert not quote_in_profile("...", PROFILE)


def test_score_is_weighted_in_code():
    result = finalize("c1", "c1.txt", JOB, PROFILE, CandidateAssessment(summary="s", assessments=[
        a("python", "met", ["Skills: Python"]),
        a("siem", "partial", ["Splunk"]),
        a("soar", "met", ["Built SOAR playbooks"]),
    ]))
    # (3*1 + 3*0.5 + 1*1) / 7
    assert result.score == round(100 * 5.5 / 7, 1)
    assert (result.must_haves_met, result.must_haves_total) == (1, 2)
    assert result.flags == []


def test_unverifiable_evidence_is_downgraded_and_flagged():
    result = finalize("c1", "c1.txt", JOB, PROFILE, CandidateAssessment(summary="s", assessments=[
        a("python", "met", ["10 years of Python at Google"]),   # hallucinated quote
        a("siem", "met", []),                                    # met with no evidence
        a("soar", "not_met"),
    ]))
    verdicts = {r.requirement_id: r.verdict for r in result.requirements}
    assert verdicts == {"python": "partial", "siem": "partial", "soar": "not_met"}
    assert not any(r.evidence_verified for r in result.requirements[:2])
    assert sum("evidence not found" in f for f in result.flags) == 2


def test_missing_assessment_scored_not_met():
    result = finalize("c1", "c1.txt", JOB, PROFILE, CandidateAssessment(summary="s", assessments=[
        a("python", "met", ["Python"]),
    ]))
    assert result.score == round(100 * 3 / 7, 1)
    assert any("no assessment returned for 'siem'" in f for f in result.flags)
    assert any("missing must-have: siem" in f for f in result.flags)
