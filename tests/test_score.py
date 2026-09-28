from shortlist_ai.schema import CandidateAssessment, JobSpec, Requirement, RequirementAssessment
from shortlist_ai.score import finalize, quote_in_profile

PROFILE = """CANDIDATE PROFILE
- Senior Security Engineer at Northwind Health (4 yrs, current role)
  * Built SOAR playbooks in Python that cut triage time by 60%
Skills: Python, Splunk, JavaScript, Microsoft Sentinel
Certifications: GCIH, OSCP"""

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


def test_labeled_list_with_items_left_out():
    # The model often shortens a list line to the items it needs.
    assert quote_in_profile("Skills: Splunk", PROFILE)
    assert quote_in_profile("Skills: JavaScript, Splunk", PROFILE)
    assert quote_in_profile("skills: microsoft sentinel", PROFILE)
    assert quote_in_profile("Certifications: OSCP", PROFILE)
    assert not quote_in_profile("Skills: Kubernetes", PROFILE)  # not in the line
    assert not quote_in_profile("Skills: Java", PROFILE)  # whole items only, not "JavaScript"
    assert not quote_in_profile("Skills: Sentinel, Kubernetes", PROFILE)  # every item must be there
    assert not quote_in_profile("Certifications: Splunk", PROFILE)  # in a different line
    assert not quote_in_profile("Tools: Splunk", PROFILE)  # no such label


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


ZOOX_JOB = JobSpec(title="Detection Engineer", requirements=[
    Requirement(id="llm", description="Practical experience using LLM APIs (or highly advanced personal projects)",
                kind="must_have"),
    Requirement(id="splunk", kind="must_have",
                description="Deep hands-on expertise with Splunk (SPL, Enterprise Security) or ElasticSIEM"),
    Requirement(id="python", description="Python scripting", kind="nice_to_have"),
])


def test_echoed_requirement_and_absence_notes_are_set_aside_not_downgraded():
    # Real cases from a local-model run: correct verdicts with real quotes, plus entries that
    # restate the requirement or say what's missing. Those used to downgrade a correct "met".
    result = finalize("c1", "c1.txt", ZOOX_JOB, PROFILE, CandidateAssessment(summary="s", assessments=[
        a("llm", "met", ["Built SOAR playbooks in Python", "Practical experience using LLM APIs"]),
        a("splunk", "partial", ["Microsoft Sentinel", "ElasticSIEM is not mentioned"]),
        a("python", "met", ["Python"]),
    ]))
    by_id = {r.requirement_id: r for r in result.requirements}
    assert {k: r.verdict for k, r in by_id.items()} == {"llm": "met", "splunk": "partial", "python": "met"}
    assert all(r.evidence_verified for r in result.requirements)
    assert by_id["llm"].evidence == ["Built SOAR playbooks in Python"]
    assert by_id["llm"].ignored_evidence == ["Practical experience using LLM APIs"]
    assert by_id["splunk"].ignored_evidence == ["ElasticSIEM is not mentioned"]
    assert all(r.unverified_quotes == [] for r in result.requirements)
    assert sum("ignored 1 evidence entry" in f for f in result.flags) == 2
    assert not any("evidence not found" in f for f in result.flags)


def test_only_echoes_left_means_no_evidence():
    result = finalize("c1", "c1.txt", ZOOX_JOB, PROFILE, CandidateAssessment(summary="s", assessments=[
        a("llm", "met", ["Practical experience using LLM APIs"]),
        a("splunk", "not_met", ["Splunk is not mentioned", "ElasticSIEM is not mentioned"]),
        a("python", "met", ["Python"]),
    ]))
    by_id = {r.requirement_id: r for r in result.requirements}
    assert by_id["llm"].verdict == "partial" and not by_id["llm"].evidence_verified
    assert by_id["splunk"].verdict == "not_met" and by_id["splunk"].evidence == []
    assert any("ignored 2 evidence entries" in f for f in result.flags)


def test_hallucinated_quotes_are_still_downgraded():
    # Not in the profile, not the requirement's wording, not an absence note: a made-up quote.
    result = finalize("c1", "c1.txt", ZOOX_JOB, PROFILE, CandidateAssessment(summary="s", assessments=[
        a("llm", "met", ["Built SOAR playbooks in Python", "Fine-tuned GPT-4 for alert triage"]),
        a("splunk", "not_met"),
        a("python", "met", ["Python"]),
    ]))
    llm = result.requirements[0]
    assert llm.verdict == "partial" and not llm.evidence_verified
    assert llm.unverified_quotes == ["Fine-tuned GPT-4 for alert triage"]  # the one that failed, not both
    assert any("'llm': evidence not found" in f for f in result.flags)


def test_report_marks_only_the_quote_that_failed():
    from shortlist_ai.report import _evidence_table
    result = finalize("c1", "c1.txt", ZOOX_JOB, PROFILE, CandidateAssessment(summary="s", assessments=[
        a("llm", "met", ["Built SOAR playbooks in Python", "Fine-tuned GPT-4 for alert triage"]),
        a("splunk", "not_met"),
        a("python", "met", ["Python"]),
    ]))
    row = next(line for line in _evidence_table(result) if line.startswith("| `llm`"))
    assert "“Built SOAR playbooks in Python”<br>" in row
    assert "“Fine-tuned GPT-4 for alert triage” ⚠️ not found in profile" in row
