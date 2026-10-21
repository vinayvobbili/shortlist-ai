import re
from datetime import date

import pytest

from shortlist_ai.blind import blind_profile, blind_roles
from shortlist_ai.prompts import request_text
from shortlist_ai.schema import (
    CandidateAssessment,
    Experience,
    JobSpec,
    Requirement,
    RequirementAssessment,
    RoleJudgment,
    RoleRelevance,
)
from shortlist_ai.score import score_candidate
from shortlist_ai.years import _union_months, assess_years, min_years

TODAY = date(2026, 9, 1)
YEARS = Requirement(id="years_security", description="4+ years of security engineering", kind="must_have")


@pytest.mark.parametrize("text, expected", [
    ("3+ years of professional data engineering experience", 3),
    ("At least 2 years coordinating clinical trials", 2),
    ("5 or more years in DevOps", 5),
    ("3-5 years of UX design", 3),
    ("1.5 yrs of on-call experience", 1.5),
    ("Python 3", None),
    ("AWS Certified Security – Specialty", None),
])
def test_min_years(text, expected):
    assert min_years(text) == expected


def test_union_months_counts_overlaps_once():
    assert _union_months([(0, 12), (6, 18), (30, 36)]) == 24


def listed_roles(prompt: str) -> list[tuple[str, list[str]]]:
    """(heading, listed work) for each role in a roles prompt."""
    roles = []
    for line in prompt.splitlines():
        if m := re.match(r"^\d+\. (.*)", line):
            roles.append((m.group(1), []))
        elif (m := re.match(r"^\s+\* (.*)", line)) and roles:
            roles[-1][1].append(m.group(1))
    return roles


class RolesBackend:
    """Marks the given role numbers as main work in the field, and `touches` as touching it. A main role
    quotes its first line of work (its heading when it lists none), or `quotes[n]` when given: pass
    quotes={n: []} for a main role with no quote."""
    def __init__(self, main, touches=(), quotes=None):
        self.main, self.touches, self.quotes, self.calls = set(main), set(touches), quotes or {}, []

    def structured(self, system, content, output_type):
        self.calls.append(output_type.__name__)
        if output_type is RoleRelevance:
            listed = listed_roles(request_text(content))

            def judged(i, heading, work):
                if i not in self.main:
                    return RoleJudgment(role=i, fit="touches" if i in self.touches else "no", reason="")
                return RoleJudgment(role=i, fit="main", reason="", evidence=self.quotes.get(i, (work or [heading])[:1]))
            return RoleRelevance(field="security engineering", roles=[
                judged(i, heading, work) for i, (heading, work) in enumerate(listed, 1)] + [
                RoleJudgment(role=99, fit="main", reason="out of range", evidence=["anything"])])
        # Main scorer: claims the years requirement is met, as the model used to.
        return CandidateAssessment(assessments=[RequirementAssessment(
            requirement_id="years_security", verdict="met", evidence=[], reasoning="10 years of experience")],
            summary="")


def test_years_add_up_across_roles(resume):
    roles = blind_roles(resume, TODAY)  # 4 yrs 6 mos current + 3 yrs 8 mos past
    a = assess_years(YEARS, 4, roles, RolesBackend({2}))
    assert a.verdict == "partial" and "3 yrs 8 mos" in a.reasoning
    a = assess_years(YEARS, 4, roles, RolesBackend({1, 2}))
    assert a.verdict == "met" and "8 yrs 2 mos" in a.reasoning and "across 2 roles" in a.reasoning
    a = assess_years(YEARS, 4, roles, RolesBackend(set()))
    assert a.verdict == "not_met" and a.evidence == []


def test_roles_that_only_touch_the_field_dont_count(resume):
    roles = blind_roles(resume, TODAY)
    a = assess_years(YEARS, 4, roles, RolesBackend(set(), touches={1, 2}))
    assert a.verdict == "not_met" and a.evidence == []
    assert "don't count: Senior Security Engineer at Northwind Health, Security Analyst II" in a.reasoning
    a = assess_years(YEARS, 4, roles, RolesBackend({1}, touches={2}))
    assert a.verdict == "met" and "4 yrs 6 mos" in a.reasoning and "don't count: Security Analyst II" in a.reasoning


def test_years_without_roles_skip_the_model():
    backend = RolesBackend({1})
    assert assess_years(YEARS, 4, [], backend).verdict == "not_met" and backend.calls == []


def test_unknown_duration_is_not_counted(resume):
    resume.experience.append(Experience(company="Fabrikam", title="Security Consultant", location=None,
                                        start_date=None, end_date=None, is_current=False, highlights=[]))
    a = assess_years(YEARS, 4, blind_roles(resume, TODAY), RolesBackend({3}))
    assert a.verdict == "partial" and "Duration unknown for: Security Consultant at Fabrikam" in a.reasoning


def test_scorer_verdict_is_replaced_and_evidence_verifies(resume):
    job = JobSpec(title="Security Engineer", requirements=[YEARS])
    profile, roles = blind_profile(resume, TODAY), blind_roles(resume, TODAY)
    backend = RolesBackend(set())
    result = score_candidate("c", "c.md", job, profile, backend, roles)
    assert result.requirements[0].verdict == "not_met"              # the model's "met" is overridden
    assert backend.calls == ["CandidateAssessment", "RoleRelevance"]

    result = score_candidate("c", "c.md", job, profile, RolesBackend({1}), roles)
    req = result.requirements[0]
    assert req.verdict == "met" and req.evidence_verified            # quotes from the role's own work
    assert req.evidence == [roles[0].highlights[0]]

    assert score_candidate("c", "c.md", job, profile, backend).requirements[0].verdict == "partial"  # no roles:
    # the model's verdict stands (downgraded from met because it quoted nothing)


def test_main_needs_a_quote_from_the_roles_own_work(resume):
    roles = blind_roles(resume, TODAY)  # 4 yrs 6 mos current + 3 yrs 8 mos past
    other_roles_line = roles[0].highlights[0]
    for quotes in ({2: []}, {2: [other_roles_line]}, {2: [roles[1].heading]}, {2: ["Ran red team exercises"]}):
        a = assess_years(YEARS, 4, roles, RolesBackend({1, 2}, quotes=quotes))
        assert a.verdict == "met" and "4 yrs 6 mos" in a.reasoning and "across 1 role" in a.reasoning
        assert "so not counted: Security Analyst II at Contoso Bank" in a.reasoning
        assert a.evidence == [roles[0].highlights[0]]
    a = assess_years(YEARS, 4, roles, RolesBackend({1}, quotes={1: []}))
    assert a.verdict == "not_met" and a.evidence == [] and "so not counted" in a.reasoning
    a = assess_years(YEARS, 4, roles, RolesBackend({2}, quotes={2: ["Tuned Splunk correlation searches"]}))
    assert a.verdict == "partial" and a.evidence == ["Tuned Splunk correlation searches"]  # a part of a line is enough


def test_role_lines_match_the_profile(resume):
    profile = blind_profile(resume, TODAY)
    assert all(f"- {r.line}" in profile for r in blind_roles(resume, TODAY))
