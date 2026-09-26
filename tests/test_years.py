import re
from datetime import date

import pytest

from shortlist_ai.blind import blind_profile, blind_roles
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


class RolesBackend:
    """Marks the given role numbers as in the field; everything else as not."""
    def __init__(self, in_field):
        self.in_field, self.calls = set(in_field), []

    def structured(self, system, content, output_type):
        self.calls.append(output_type.__name__)
        if output_type is RoleRelevance:
            n = len(re.findall(r"^\d+\. ", content[0]["text"], re.M))
            return RoleRelevance(field="security engineering", roles=[
                RoleJudgment(role=i, in_field=i in self.in_field, reason="") for i in range(1, n + 1)] + [
                RoleJudgment(role=99, in_field=True, reason="out of range")])
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
    assert req.verdict == "met" and req.evidence_verified            # role lines are quoted from the profile
    assert req.evidence == ["Senior Security Engineer at Northwind Health (4 yrs 6 mos, current role)"]

    assert score_candidate("c", "c.md", job, profile, backend).requirements[0].verdict == "partial"  # no roles:
    # the model's verdict stands (downgraded from met because it quoted nothing)


def test_role_lines_match_the_profile(resume):
    profile = blind_profile(resume, TODAY)
    assert all(f"- {r.line}" in profile for r in blind_roles(resume, TODAY))
