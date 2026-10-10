import pytest

from shortlist_ai import prompts as P
from shortlist_ai.blind import Role
from shortlist_ai.extract import Cache, extract_job
from shortlist_ai.pipeline import match_jobs
from shortlist_ai.prompts import PROMPTS, PromptError, resolve
from shortlist_ai.schema import (
    CandidateAssessment,
    JobSpec,
    Requirement,
    RequirementAssessment,
    Resume,
    RoleJudgment,
    RoleRelevance,
)
from shortlist_ai.score import build_prompt
from shortlist_ai.years import assess_years, roles_prompt

JOB = JobSpec(title="Robotics Engineer", requirements=[
    Requirement(id="ros", description="ROS", kind="must_have"),
    Requirement(id="years", description="3+ years of robotics", kind="nice_to_have"),
])
ROLES = [Role(heading="Engineer at Acme Robotics", line="Engineer at Acme Robotics (1 yr)",
              highlights=["Built arm controllers"], span=(0, 12))]


class RecordingBackend:
    """Records each call's system prompt and request text; meets every requirement with the skills line."""
    name, model, reads_documents = "fake", "fake-1", False

    def __init__(self):
        self.calls: list[tuple[str, str, str]] = []  # (output type, system, request text)

    def structured(self, system, content, output_type):
        text = content[0]["text"]
        self.calls.append((output_type.__name__, system, text))
        if output_type is Resume:
            return Resume(full_name="Dana Acme", email=None, phone=None, location=None, links=[], summary=None,
                          experience=[], education=[], skills=["ROS"], certifications=[], languages=[])
        if output_type is JobSpec:
            return JOB
        if output_type is RoleRelevance:
            return RoleRelevance(field="robotics", roles=[RoleJudgment(role=1, fit="no", reason="")])
        return CandidateAssessment(summary="", assessments=[
            RequirementAssessment(requirement_id="ros", verdict="met", evidence=["Skills: ROS"], reasoning="")])

    def systems(self, kind: str) -> list[str]:
        return [system for k, system, _ in self.calls if k == kind]

    def requests(self, kind: str) -> list[str]:
        return [text for k, _, text in self.calls if k == kind]


def test_every_prompt_has_a_name_an_about_and_its_default():
    assert list(PROMPTS) == ["resume_system", "job_system", "score_system", "score_request", "years_system",
                             "years_request"]
    assert all(p.about and p.default for p in PROMPTS.values())
    assert resolve() == {name: p.default for name, p in PROMPTS.items()}
    assert PROMPTS["score_request"].placeholders == ("title", "requirements", "profile")


def test_default_requests_are_unchanged():
    # Byte for byte what the model saw before prompts could be edited: evals and caches stay comparable.
    assert build_prompt(JOB, "Skills: ROS")[0]["text"] == (
        "Role: Robotics Engineer\n\nRequirements:\n- id=ros [must_have]: ROS\n"
        "- id=years [nice_to_have]: 3+ years of robotics\n\n<profile>\nSkills: ROS\n</profile>\n\n"
        "Assess every requirement.")
    assert roles_prompt(JOB.requirements[1], ROLES)[0]["text"] == (
        "Requirement: 3+ years of robotics\n\nRoles:\n1. Engineer at Acme Robotics\n   * Built arm controllers"
        "\n\nJudge every role.")


def test_old_constant_names_still_import():
    from shortlist_ai.extract import JOB_SYSTEM, RESUME_SYSTEM
    from shortlist_ai.score import SCORE_SYSTEM
    from shortlist_ai.years import ROLES_SYSTEM
    assert (RESUME_SYSTEM, JOB_SYSTEM, SCORE_SYSTEM, ROLES_SYSTEM) == (
        P.RESUME_SYSTEM, P.JOB_SYSTEM, P.SCORE_SYSTEM, P.YEARS_SYSTEM)


@pytest.mark.parametrize("overrides, message", [
    ({"tone": "Be kind."}, "unknown prompt 'tone'"),
    ({"score_system": "  "}, "is empty"),
    ({"score_request": "Role: {title}\n{requirements}"}, "must keep {profile}"),
    ({"score_request": "{title} {requirements} {profile} {salary}"}, "unknown placeholder(s) {salary}"),
    ({"score_request": "{title} {requirements} {profile} {"}, "write a literal brace as {{ or }}"),
    ({"years_request": "{requirement} {roles} {roles.0}"}, "unknown placeholder(s) {roles.0}"),
])
def test_bad_overrides_say_what_is_wrong(overrides, message):
    with pytest.raises(PromptError) as e:
        resolve(overrides)
    assert message in str(e.value)


def test_system_prompts_are_sent_as_written_braces_and_all():
    assert resolve({"score_system": "Judge {strictly}."})["score_system"] == "Judge {strictly}."


def test_literal_braces_in_a_request_template():
    template = "{{json}} {title}\n{requirements}\n<profile>\n{profile}\n</profile>"
    text = build_prompt(JOB, "Skills: ROS", {"score_request": template})[0]["text"]
    assert text.startswith("{json} Robotics Engineer\n- id=ros")


def test_match_jobs_uses_overrides_and_keeps_the_rest(tmp_path):
    (tmp_path / "dana.txt").write_text("Dana Acme\nSkills: ROS\n")
    backend = RecordingBackend()
    overrides = {"score_system": "Be strict.", "score_request": "Job {title}\n{requirements}\nProfile:\n{profile}"}
    matches = match_jobs(tmp_path / "dana.txt", {"acme": JOB}, backend, prompts=overrides)
    assert not matches.errors and matches.matches[0].result.must_haves_met == 1
    assert backend.systems("CandidateAssessment") == ["Be strict."]
    assert backend.requests("CandidateAssessment")[0].startswith("Job Robotics Engineer\n- id=ros")
    assert backend.systems("Resume") == [P.RESUME_SYSTEM]


def test_a_bad_override_fails_before_any_model_call(tmp_path):
    (tmp_path / "dana.txt").write_text("Dana Acme\nSkills: ROS\n")
    backend = RecordingBackend()
    with pytest.raises(PromptError, match="must keep"):
        match_jobs(tmp_path / "dana.txt", {"acme": JOB}, backend, prompts={"score_request": "{title}"})
    assert backend.calls == []


def test_years_prompts_can_be_edited():
    backend = RecordingBackend()
    assess_years(JOB.requirements[1], 3, ROLES, backend,
                 {"years_system": "Count robotics roles.", "years_request": "R: {requirement}\n{roles}"})
    assert backend.calls == [("RoleRelevance", "Count robotics roles.",
                              "R: 3+ years of robotics\n1. Engineer at Acme Robotics\n   * Built arm controllers")]


def test_an_edited_extraction_prompt_extracts_afresh(tmp_path):
    posting = tmp_path / "acme.md"
    posting.write_text("Acme Robotics is hiring a Robotics Engineer. Must know ROS.")
    cache, backend = Cache(tmp_path / "cache"), RecordingBackend()
    extract_job(posting, backend, cache)
    extract_job(posting, backend, cache)
    extract_job(posting, backend, cache, {"job_system": "List only must-haves."})
    extract_job(posting, backend, cache, {"job_system": "List only must-haves."})
    assert backend.systems("JobSpec") == [P.JOB_SYSTEM, "List only must-haves."]
