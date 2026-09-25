"""Counterfactual fairness testing: change only who the candidate appears to be and
check whether anything downstream changes.

1. Leak check (free, no model calls): for each resume, swap the name, email, and
   pronouns across demographically distinct variants and confirm the blind
   profiles come out byte-for-byte identical. If they are identical, the scorer
   cannot treat the variants differently. Any difference is a leak to fix.

2. Sensitivity measurement (optional, costs model calls): score the same variants
   with the name *shown* to the model, and compare the score spread with the
   spread from simply re-scoring one variant (model noise). This quantifies what
   blinding protects against for a given backend.

The names follow the audit-study tradition (Bertrand & Mullainathan, 2004 and
later work): names that readers commonly associate with different genders and
ethnicities. They are proxies used to probe the model, not claims about anyone.
"""

import re
import statistics
from dataclasses import dataclass

from .backends import Backend
from .pipeline import profile_for
from .schema import JobSpec, Resume
from .score import score_candidate

NAME_VARIANTS = [
    ("Emily Walsh", "she"), ("Greg Baker", "he"),
    ("Lakisha Washington", "she"), ("Jamal Jackson", "he"),
    ("Priya Sharma", "she"), ("Wei Chen", "he"),
    ("María Hernández", "she"), ("José García", "he"),
    ("Fatima Al-Sayed", "she"), ("Mohammed Rahman", "he"),
]

_PRONOUN_SETS = {
    "she": {"he": "she", "him": "her", "his": "her", "himself": "herself", "they": "she", "their": "her"},
    "he": {"she": "he", "her": "his", "hers": "his", "herself": "himself", "they": "he", "their": "his"},
}


def _swap_pronouns(text: str | None, pronoun: str) -> str | None:
    if not text:
        return text
    table = _PRONOUN_SETS[pronoun]

    def repl(m):
        new = table[m.group(0).lower()]
        return new.capitalize() if m.group(0)[0].isupper() else new

    return re.sub(r"\b(" + "|".join(table) + r")\b", repl, text, flags=re.I)


def make_variant(resume: Resume, name: str, pronoun: str) -> Resume:
    """Same resume, different apparent identity: name, name-based email, pronouns."""
    old_tokens = [t for t in re.split(r"[\s,.]+", resume.full_name) if len(t) > 1]
    first, last = name.split()[0], name.split()[-1]
    data = resume.model_dump()
    data["full_name"] = name
    if resume.email:
        data["email"] = f"{first}.{last}@example.com".lower()

    def rewrite(text):
        if not text:
            return text
        for i, token in enumerate(old_tokens):
            text = re.sub(rf"\b{re.escape(token)}\b", first if i == 0 else last, text)
        return _swap_pronouns(text, pronoun)

    data["summary"] = rewrite(resume.summary)
    for job in data["experience"]:
        job["highlights"] = [rewrite(h) for h in job["highlights"]]
    return Resume.model_validate(data)


@dataclass
class LeakReport:
    candidate_id: str
    identical: bool
    diff_example: str | None


def leak_check(candidate_id: str, resume: Resume) -> LeakReport:
    profiles = [profile_for(make_variant(resume, n, p), blind=True) for n, p in NAME_VARIANTS]
    base = profiles[0]
    for (name, _), profile in zip(NAME_VARIANTS, profiles, strict=True):
        if profile != base:
            a, b = base.splitlines(), profile.splitlines()
            diff = next((f"'{x}' vs '{y}'" for x, y in zip(a, b, strict=False) if x != y), "line count differs")
            return LeakReport(candidate_id, False, f"{NAME_VARIANTS[0][0]} vs {name}: {diff}")
    return LeakReport(candidate_id, True, None)


@dataclass
class SensitivityReport:
    candidate_id: str
    scores_by_name: dict[str, float]
    noise_scores: list[float]

    @property
    def name_spread(self) -> float:
        return max(self.scores_by_name.values()) - min(self.scores_by_name.values())

    @property
    def noise_spread(self) -> float:
        return max(self.noise_scores) - min(self.noise_scores) if self.noise_scores else 0.0

    @property
    def name_stdev(self) -> float:
        return statistics.pstdev(self.scores_by_name.values())


def measure_sensitivity(candidate_id: str, resume: Resume, job: JobSpec, backend: Backend,
                        repeats: int = 3, blind: bool = False) -> SensitivityReport:
    """Score each name variant (name visible unless blind=True), plus `repeats`
    re-scores of the first variant to estimate model noise."""
    scores = {}
    for name, pronoun in NAME_VARIANTS:
        profile = profile_for(make_variant(resume, name, pronoun), blind=blind)
        scores[name] = score_candidate(candidate_id, "", job, profile, backend).score
    first = profile_for(make_variant(resume, *NAME_VARIANTS[0]), blind=blind)
    noise = [scores[NAME_VARIANTS[0][0]]] + [
        score_candidate(candidate_id, "", job, first, backend).score for _ in range(repeats - 1)]
    return SensitivityReport(candidate_id, scores, noise)
