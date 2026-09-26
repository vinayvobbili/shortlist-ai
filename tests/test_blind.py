from datetime import date

from shortlist_ai.blind import blind_profile, format_duration, months_between, total_experience_months
from shortlist_ai.schema import Experience

TODAY = date(2026, 9, 1)


def test_identity_signals_removed(resume):
    profile = blind_profile(resume, TODAY)
    for leaked in ["Priya", "Raman", "priya.raman@example.com", "555-0142", "linkedin.com",
                   "Seattle", "Charlotte", "Georgia Tech", "2018", "2022", "Ms."]:
        assert leaked not in profile, leaked


def test_pronouns_neutralized(resume):
    profile = blind_profile(resume, TODAY)
    assert " she " not in profile and " her " not in profile
    assert "they led IR" in profile and "led their team" in profile


def test_job_content_kept(resume):
    profile = blind_profile(resume, TODAY)
    for kept in ["Senior Security Engineer", "Northwind Health", "SOAR playbooks", "Splunk",
                 "B.S. Computer Science", "GCIH", "Tamil", "ASP.NET"]:
        assert kept in profile, kept


def test_durations_replace_dates(resume):
    profile = blind_profile(resume, TODAY)
    assert "(4 yrs 6 mos, current role)" in profile   # 2022-03 .. 2026-09
    assert "(3 yrs 8 mos, past role)" in profile      # 2018-06 .. 2022-02


def test_overlapping_roles_not_double_counted(resume):
    resume.experience.append(Experience(company="Community College", title="Adjunct", location=None,
                                        start_date="2020-01", end_date="2021-01", is_current=False, highlights=[]))
    # 2018-06..2022-02 and 2022-03..2026-09 -> 44 + 54 months; the adjunct role overlaps entirely
    assert total_experience_months(resume, TODAY) == 98


def test_duration_helpers():
    assert months_between("2021", "2023", TODAY) == 24
    assert months_between(None, "2023", TODAY) is None
    assert format_duration(13) == "1 yr 1 mo"
    assert format_duration(0) == "under 1 mo"
    assert format_duration(None) == "duration unknown"
