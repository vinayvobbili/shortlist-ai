from shortlist_ai.fairness import NAME_VARIANTS, SensitivityReport, leak_check, make_variant, measure_sensitivity
from shortlist_ai.pipeline import profile_for
from shortlist_ai.schema import CandidateAssessment, JobSpec, Requirement, RequirementAssessment


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


def test_gender_gap():
    scores = {n: (60.0 if p == "she" else 50.0) for n, p in NAME_VARIANTS}
    assert SensitivityReport("c1", scores, []).gender_gap == 10.0


class NameEchoBackend:
    """Meets the requirement only for names starting with J; records every prompt."""
    def __init__(self):
        self.prompts = []

    def structured(self, system, content, output_type):
        text = content[0]["text"]
        self.prompts.append(text)
        verdict = "met" if "Name: J" in text else "not_met"
        return CandidateAssessment(summary="", assessments=[RequirementAssessment(
            requirement_id=r, verdict=verdict, evidence=["Skills"] if verdict == "met" else [], reasoning="")
            for r in ("python", "sql")])


def test_sensitivity_names_differ_only_by_name_line(resume):
    job = JobSpec(title="Engineer", requirements=[
        Requirement(id="python", kind="must_have", description="Python"),
        Requirement(id="sql", kind="must_have", description="SQL")])
    backend = NameEchoBackend()
    rep = measure_sensitivity("c1", resume, job, backend)
    assert rep.scores_by_name["Jamal Jackson"] == 100 and rep.scores_by_name["Emily Walsh"] == 0
    assert len(rep.noise_scores) == len(NAME_VARIANTS)  # same sample size as the names
    profiles = {t.split("<profile>")[1].split("\n", 2)[2] for t in backend.prompts}
    assert len(profiles) == 1  # everything after the name line is identical
