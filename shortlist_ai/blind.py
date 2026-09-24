"""Stage 2: build a blind candidate profile for scoring.

The scorer never sees the original resume, only this profile, which is rendered
from the extracted fields with identity signals removed:

  removed    name, email, phone, links, home location, job locations,
             school names, graduation years, calendar dates
  rewritten  dates -> durations ("4 yrs 2 mos"), so experience length stays
             visible but age can't be inferred from when someone graduated or
             started working; gendered pronouns and honorifics -> neutral;
             the candidate's name and contact details scrubbed from free text
  kept       job titles, companies, highlights, skills, certifications,
             degree types and subjects, spoken languages

This reduces the signals a model could discriminate on; it does not eliminate
them (writing style, company names and activities can still carry signal).
`shortlist fairness` tests how well it holds up.
"""

import re
from datetime import date

from .schema import Resume

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# Bare domains only for profile hosts: a generic "word.net" rule would mangle skills
# like ASP.NET. The resume's own link URLs are also removed verbatim in blind_profile.
_URL = re.compile(r"\b(?:https?://|www\.)\S+|\b(?:linkedin|github|gitlab|twitter|x|medium|behance|dribbble)"
                  r"\.com(?:/\S*)?", re.I)
_PHONE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
_HONORIFIC = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Mx|Sir|Madam)\.?(?=\s)", re.I)
_PRONOUNS = {
    "he": "they", "she": "they", "him": "them", "his": "their", "her": "their",
    "hers": "theirs", "himself": "themselves", "herself": "themselves",
}
_PRONOUN = re.compile(r"\b(" + "|".join(_PRONOUNS) + r")\b", re.I)


def scrub(text: str, name_tokens: set[str]) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _URL.sub("[link]", text)
    text = _PHONE.sub("[phone]", text)
    text = _HONORIFIC.sub("", text)

    def pronoun(m):
        repl = _PRONOUNS[m.group(1).lower()]
        return repl.capitalize() if m.group(1)[0].isupper() else repl

    text = _PRONOUN.sub(pronoun, text)
    for token in name_tokens:
        text = re.sub(rf"\b{re.escape(token)}\b", "[candidate]", text, flags=re.I)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _parse_ym(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    m = re.fullmatch(r"(\d{4})(?:-(\d{1,2}))?", value.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2) or 1)


def months_between(start: str | None, end: str | None, today: date | None = None) -> int | None:
    begin = _parse_ym(start)
    if begin is None:
        return None
    today = today or date.today()
    finish = _parse_ym(end) or (today.year, today.month)
    return max(0, (finish[0] - begin[0]) * 12 + finish[1] - begin[1])


def format_duration(months: int | None) -> str:
    if months is None:
        return "duration unknown"
    years, rem = divmod(months, 12)
    parts = ([f"{years} yr{'s' if years != 1 else ''}"] if years else []) + \
            ([f"{rem} mo{'s' if rem != 1 else ''}"] if rem else [])
    return " ".join(parts) or "under 1 mo"


def total_experience_months(resume: Resume, today: date | None = None) -> int:
    """Union of job date ranges, so overlapping roles aren't double-counted."""
    spans = []
    for job in resume.experience:
        begin = _parse_ym(job.start_date)
        if begin is None:
            continue
        t = today or date.today()
        finish = _parse_ym(job.end_date) or (t.year, t.month)
        spans.append((begin[0] * 12 + begin[1], finish[0] * 12 + finish[1]))
    total, current_end = 0, None
    for s, e in sorted(spans):
        if current_end is None or s > current_end:
            total += e - s
            current_end = e
        elif e > current_end:
            total += e - current_end
            current_end = e
    return total


def blind_profile(resume: Resume, today: date | None = None) -> str:
    name_tokens = {t for t in re.split(r"[\s,.]+", resume.full_name) if len(t) > 1}
    # Also scrub exact contact values in case the regexes miss an unusual format.
    literals = [v for v in (resume.email, resume.phone, *[l.url for l in resume.links]) if v]

    def clean(text: str) -> str:
        for lit in literals:
            text = text.replace(lit, "[redacted]")
        return scrub(text, name_tokens)

    lines = ["CANDIDATE PROFILE"]
    if resume.summary:
        lines += ["", "Summary:", clean(resume.summary)]

    lines += ["", f"Experience (total {format_duration(total_experience_months(resume, today))}):"]
    if not resume.experience:
        lines.append("- none listed")
    for job in resume.experience:
        status = "current role" if job.is_current else "past role"
        duration = format_duration(months_between(job.start_date, job.end_date, today))
        lines.append(f"- {clean(job.title)} at {clean(job.company)} ({duration}, {status})")
        lines += [f"  * {clean(h)}" for h in job.highlights]

    lines += ["", "Education:"]
    if not resume.education:
        lines.append("- none listed")
    for edu in resume.education:
        credential = " ".join(x for x in (edu.degree, edu.field_of_study) if x) or "credential"
        lines.append(f"- {clean(credential)}")

    for label, items in (("Skills", resume.skills), ("Certifications", resume.certifications),
                         ("Spoken languages", resume.languages)):
        if items:
            lines += ["", f"{label}: " + ", ".join(clean(i) for i in items)]
    return "\n".join(lines)
