"""Data models. The LLM-facing models double as structured-output schemas, so their
field descriptions are part of the prompt."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Resumes
# ---------------------------------------------------------------------------


class Link(BaseModel):
    label: str = Field(description="e.g. LinkedIn, GitHub, Portfolio")
    url: str


class Experience(BaseModel):
    company: str
    title: str
    location: Optional[str]
    start_date: Optional[str] = Field(
        description="YYYY-MM, or YYYY alone if the resume gives only the year (never invent a month)")
    end_date: Optional[str] = Field(description="Same format as start_date; null if this is the current role")
    is_current: bool
    highlights: list[str] = Field(description="Achievements/responsibilities, one per bullet, original wording")


class Education(BaseModel):
    institution: str
    degree: Optional[str] = Field(
        description="Degree or credential type only, as written (e.g. 'B.A.', 'MBA', 'Diploma'); "
                    "the subject goes in field_of_study")
    field_of_study: Optional[str] = Field(description="Subject/major, abbreviations written out in full")
    graduation_year: Optional[int]


class Resume(BaseModel):
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    links: list[Link]
    summary: Optional[str] = Field(description="The candidate's own summary/objective, if present")
    experience: list[Experience] = Field(description="Most recent first")
    education: list[Education]
    skills: list[str] = Field(
        description="Deduplicated, canonical names (e.g. 'JavaScript' not 'JS'). Include tools and "
                    "technologies named in job descriptions, not only the skills section. "
                    "Do not repeat certifications here.")
    certifications: list[str] = Field(description="Certification names as written in the resume")
    languages: list[str] = Field(description="Spoken language names only, without proficiency levels")


# ---------------------------------------------------------------------------
# Job descriptions
# ---------------------------------------------------------------------------


class Requirement(BaseModel):
    id: str = Field(description="Short snake_case identifier, e.g. 'python' or 'gcp_data_pipelines'")
    description: str = Field(description="One specific, checkable requirement in plain language")
    kind: Literal["must_have", "nice_to_have"] = Field(
        description="must_have only if the posting says required/must/minimum; otherwise nice_to_have")


class JobSpec(BaseModel):
    title: str
    requirements: list[Requirement] = Field(
        description="Job-related qualifications only (skills, experience, certifications, domain "
                    "knowledge). Exclude perks, company boilerplate, and anything about age, gender, "
                    "nationality, health, family status, or other protected characteristics.")


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


class RequirementAssessment(BaseModel):
    requirement_id: str
    verdict: Literal["met", "partial", "not_met"]
    evidence: list[str] = Field(
        description="Verbatim quotes copied exactly from the candidate profile that support the "
                    "verdict. Empty if not_met. Never paraphrase.")
    reasoning: str = Field(description="One sentence explaining the verdict")


class CandidateAssessment(BaseModel):
    """What the LLM returns for one candidate. The numeric score is computed in code."""
    assessments: list[RequirementAssessment]
    summary: str = Field(description="Two sentences: main strengths and main gaps for this role")


class ScoredRequirement(RequirementAssessment):
    kind: Literal["must_have", "nice_to_have"]
    evidence_verified: bool = Field(description="Every evidence quote was found in the candidate profile")


class CandidateResult(BaseModel):
    candidate_id: str
    source_file: str
    score: float = Field(description="0-100, weighted from requirement verdicts")
    must_haves_met: int
    must_haves_total: int
    requirements: list[ScoredRequirement]
    summary: str
    flags: list[str] = Field(default_factory=list)
