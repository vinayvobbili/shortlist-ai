from shortlist_ai.schema import CandidateAssessment, JobSpec, Requirement, RequirementAssessment
from shortlist_ai.score import SCORE_SYSTEM, finalize, quote_in_profile

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


def test_rules_say_how_and_and_or_lists_are_met():
    # "reverse engineering and security analysis" got full credit from malware forensics alone.
    assert 'joins items with "and": met needs evidence for each item' in SCORE_SYSTEM
    assert 'joins items with "or": evidence for one item is enough' in SCORE_SYSTEM


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


WIDGET_JOB = JobSpec(title="Senior Widget Engineer", requirements=[
    Requirement(id="widgets", description="Widget kernel development", kind="must_have", core=True),
    Requirement(id="python", description="Python scripting", kind="must_have"),
    Requirement(id="degree", description="Bachelor's degree", kind="must_have"),
])
WIDGET_PROFILE = "Skills: Python, Widget kernels\nEducation: B.S. Computer Science, Initech"


def widget_result(widgets_verdict, job=WIDGET_JOB):
    ev = ["Skills: Widget kernels"] if widgets_verdict != "not_met" else []
    return finalize("c1", "c1.txt", job, WIDGET_PROFILE, CandidateAssessment(summary="s", assessments=[
        a("widgets", widgets_verdict, ev),
        a("python", "met", ["Skills: Python"]),
        a("degree", "met", ["B.S. Computer Science"]),
    ]))


def test_core_not_met_caps_the_score_at_40_and_says_so():
    result = widget_result("not_met")
    assert result.score == 40.0  # uncapped: 100 * 6 / 9 = 66.7
    assert "core requirement 'widgets' not met: score capped at 40 (was 66.7)" in result.flags
    assert [r.core for r in result.requirements] == [True, False, False]


def test_core_partial_caps_the_score_at_65():
    result = widget_result("partial")
    assert result.score == 65.0  # uncapped: 100 * 7.5 / 9 = 83.3
    assert "core requirement 'widgets' partial: score capped at 65 (was 83.3)" in result.flags


def test_core_met_is_not_capped():
    result = widget_result("met")
    assert result.score == 100.0 and result.flags == []


def test_a_gap_that_is_not_core_is_not_capped():
    job = JobSpec(title="Senior Widget Engineer", requirements=[
        r.model_copy(update={"core": False}) for r in WIDGET_JOB.requirements])
    result = widget_result("not_met", job)
    assert result.score == round(100 * 6 / 9, 1)
    assert not any("capped" in f for f in result.flags)


def test_a_score_already_under_the_cap_is_left_alone():
    job = JobSpec(title="Globex Widget Role", requirements=[
        Requirement(id="widgets", description="Widgets", kind="must_have", core=True),
        Requirement(id="a", description="A", kind="must_have"),
        Requirement(id="b", description="B", kind="must_have"),
    ])
    result = finalize("c1", "c1.txt", job, "Skills: Python", CandidateAssessment(summary="s", assessments=[
        a("widgets", "not_met"), a("a", "not_met"), a("b", "met", ["Skills: Python"])]))
    assert result.score == round(100 / 3, 1)
    assert not any("capped" in f for f in result.flags)


def test_a_job_spec_saved_without_core_still_loads():
    old = {"title": "Widget Engineer", "requirements": [
        {"id": "python", "description": "Python", "kind": "must_have"}]}
    job = JobSpec.model_validate(old)
    assert job.requirements[0].core is False


def test_the_job_prompt_asks_for_core_requirements():
    from shortlist_ai.prompts import JOB_SYSTEM
    assert "core" in JOB_SYSTEM and "overview and responsibilities" in JOB_SYSTEM


def test_report_marks_core_requirements():
    from shortlist_ai.report import _evidence_table
    assert "`widgets` ★ core" in "\n".join(_evidence_table(widget_result("met")))
