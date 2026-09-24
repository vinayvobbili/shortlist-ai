from shortlist_ai.fairness import NAME_VARIANTS, leak_check, make_variant
from shortlist_ai.pipeline import profile_for


def test_variants_change_identity_only(resume):
    v = make_variant(resume, "Jamal Jackson", "he")
    assert v.full_name == "Jamal Jackson" and v.email == "jamal.jackson@example.com"
    assert "Jamal" in v.summary and " he " in v.summary
    assert v.skills == resume.skills and v.experience[0].title == resume.experience[0].title


def test_blind_profiles_identical_across_variants(resume):
    report = leak_check("c1", resume)
    assert report.identical, report.diff_example


def test_leak_check_catches_a_broken_scrubber(resume, monkeypatch):
    # If free-text scrubbing regresses, names and pronouns reach the profile and differ by variant.
    monkeypatch.setattr("shortlist_ai.blind.scrub", lambda text, name_tokens: text)
    report = leak_check("c1", resume)
    assert not report.identical and "Emily" in report.diff_example


def test_unblinded_profiles_differ(resume):
    profiles = {profile_for(make_variant(resume, n, p), blind=False) for n, p in NAME_VARIANTS}
    assert len(profiles) == len(NAME_VARIANTS)
