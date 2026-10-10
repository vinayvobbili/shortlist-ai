"""Stage 1: extract structured data from resumes and job descriptions (cached)."""

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .backends import Backend
from .documents import LoadedDocument, load_document
from .prompts import JOB_SYSTEM as JOB_SYSTEM  # the prompts live in prompts.py; still importable from here
from .prompts import RESUME_SYSTEM as RESUME_SYSTEM
from .prompts import resolve
from .schema import JobSpec, Resume

# Cache keys cover the prompt, schema and exact content sent; bump this only for other changes.
CACHE_VERSION = "2"
DEFAULT_CACHE_DIR = Path(".shortlist-cache")


class Cache:
    """Model outputs on disk, keyed by everything that determines them."""

    def __init__(self, directory: Path | None = DEFAULT_CACHE_DIR):
        self.directory = directory

    def _path(self, kind: str, backend: Backend, system: str, content: list[dict], model_type) -> Path | None:
        if self.directory is None:
            return None
        material = json.dumps([CACHE_VERSION, backend.name, backend.model, system,
                               model_type.model_json_schema(), content], sort_keys=True)
        return self.directory / kind / f"{hashlib.sha256(material.encode()).hexdigest()[:20]}.json"

    def call(self, kind: str, backend: Backend, system: str, content: list[dict], model_type):
        path = self._path(kind, backend, system, content, model_type)
        if path and path.exists():
            return model_type.model_validate_json(path.read_text())
        value = backend.structured(system, content, model_type)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value.model_dump_json(indent=2))
        return value


def _content(doc: LoadedDocument, backend: Backend, label: str) -> list[dict]:
    # A PDF with hidden text goes in as its visible text only, so no backend reads the hidden part.
    if backend.reads_documents and doc.pdf_base64 and not doc.hidden_text:
        return [*doc.content_blocks(), {"type": "text", "text": f"Extract this {label}."}]
    if not doc.text.strip():
        # Checked here, not in the backend: once wrapped in a prompt the text is never
        # empty, and a model given an empty resume returns an empty (or invented) one.
        raise ValueError(f"{doc.path.name} has no text layer (scanned PDF?). "
                         f"Use a backend that reads documents (--backend claude) or OCR it first.")
    return [{"type": "text", "text": f"<{label}>\n{doc.text}\n</{label}>\n\nExtract this {label}."}]


@dataclass
class ExtractedResume:
    resume: Resume
    flags: list[str] = field(default_factory=list)   # for the human reviewer


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9+#]", "", s.lower())


def ground(resume: Resume, doc: LoadedDocument) -> ExtractedResume:
    """Drop skills and certifications that don't appear in the visible text.

    These short lists are what keyword-stuffing and injected instructions target, and they feed
    straight into scoring. Exact matching can also drop a skill the model renamed (resume says
    "JS", model wrote "JavaScript"), so every drop is flagged rather than silent. Skipped when
    there is no text layer to check against (scans read by a vision backend).
    """
    flags = []
    if doc.hidden_text:
        snippet = doc.hidden_text[:80] + ("..." if len(doc.hidden_text) > 80 else "")
        flags.append(f"PDF contains hidden text (a reader can't see it), excluded from extraction: '{snippet}'")
    if not doc.text.strip():
        return ExtractedResume(resume, flags)
    text = _norm(doc.text)
    kept = {}
    for name in ("skills", "certifications"):
        items = getattr(resume, name)
        kept[name] = [x for x in items if _norm(x) and _norm(x) in text]
        if dropped := [x for x in items if x not in kept[name]]:
            flags.append(f"{name} not found in the document text, removed: {', '.join(dropped)}")
    return ExtractedResume(resume.model_copy(update=kept), flags)


def extract_resume(path: Path, backend: Backend, cache: Cache | None = None,
                   prompts: Mapping[str, str] | None = None) -> ExtractedResume:
    """prompts: {name: text} in place of the defaults (see prompts.py); uses resume_system."""
    system = resolve(prompts)["resume_system"]
    cache = cache or Cache(None)
    doc = load_document(path)
    resume = cache.call("resumes", backend, system, _content(doc, backend, "resume"), Resume)
    return ground(resume, doc)


def extract_job(path: Path, backend: Backend, cache: Cache | None = None,
                prompts: Mapping[str, str] | None = None) -> JobSpec:
    """prompts: {name: text} in place of the defaults (see prompts.py); uses job_system."""
    system = resolve(prompts)["job_system"]
    cache = cache or Cache(None)
    doc = load_document(path)
    job = cache.call("jobs", backend, system, _content(doc, backend, "job_posting"), JobSpec)
    _check_unique_ids(job)
    return job


def load_job_spec(path: Path) -> JobSpec:
    """Load a (possibly hand-edited) requirements file written by `shortlist requirements`."""
    job = JobSpec.model_validate(json.loads(path.read_text()))
    _check_unique_ids(job)
    return job


def _check_unique_ids(job: JobSpec):
    ids = [r.id for r in job.requirements]
    if len(ids) != len(set(ids)):
        # Make them unique rather than fail: ids only need to be stable within one run.
        seen: dict[str, int] = {}
        for r in job.requirements:
            n = seen.get(r.id, 0)
            seen[r.id] = n + 1
            if n:
                r.id = f"{r.id}_{n + 1}"
    if not job.requirements:
        raise ValueError("The job description produced no requirements.")
