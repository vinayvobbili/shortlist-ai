from datetime import date

from shortlist_ai.blind import blind_profile, format_duration, months_between

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


def test_no_total_across_roles(resume):
    # A total invites counting unrelated years toward "N+ years of X"; only per-role durations are shown.
    profile = blind_profile(resume, TODAY)
    assert "Experience:\n" in profile and "total" not in profile


def test_duration_helpers():
    assert months_between("2021", "2023", TODAY) == 24
    assert months_between(None, "2023", TODAY) is None
    assert format_duration(13) == "1 yr 1 mo"
    assert format_duration(0) == "under 1 mo"
    assert format_duration(None) == "duration unknown"
