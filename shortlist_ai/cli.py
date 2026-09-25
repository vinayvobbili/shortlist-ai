"""Command-line interface: `shortlist <command>`."""

import argparse
import sys
from pathlib import Path

from .backends import BackendError, get_backend
from .documents import SUPPORTED
from .extract import DEFAULT_CACHE_DIR, Cache, extract_job, extract_resume, load_job_spec


def _progress(msg: str):
    print(f"  {msg}", file=sys.stderr, flush=True)


def _resume_paths(folder: Path) -> list[Path]:
    paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED and not p.name.startswith("."))
    if not paths:
        raise SystemExit(f"No resumes ({', '.join(sorted(SUPPORTED))}) found in {folder}")
    return paths


def _job(args, backend, cache):
    if args.requirements:
        return load_job_spec(args.requirements)
    if not args.jd:
        raise SystemExit("Provide --jd (a job description) or --requirements (a reviewed requirements file).")
    return extract_job(args.jd, backend, cache)


def _backend_desc(backend) -> str:
    return f"{backend.name}:{backend.model}"


def _write(text: str, out: Path | None):
    if out:
        out.write_text(text, encoding="utf-8")
        print(f"Wrote {out}", file=sys.stderr)
    else:
        print(text)


def _cost_note(backend):
    usage = getattr(backend, "usage", None)
    if usage and usage.calls:
        cost = usage.cost_usd(backend.model)
        extra = f", ~${cost:.2f}" if cost else ""
        print(f"{usage.calls} model calls, {usage.input_tokens:,} in / {usage.output_tokens:,} out tokens{extra}",
              file=sys.stderr)


def cmd_requirements(args, backend, cache):
    job = extract_job(args.jd, backend, cache)
    _write(job.model_dump_json(indent=2), args.out)
    if args.out:
        print("Review and edit the requirements, then pass the file with --requirements.", file=sys.stderr)


def cmd_rank(args, backend, cache):
    from .pipeline import rank
    from .report import to_json, to_markdown

    job = _job(args, backend, cache)
    ranking = rank(job, _resume_paths(args.resumes), backend, cache=cache, prefilter_k=args.prefilter_k,
                   workers=args.workers, progress=_progress)
    if args.format == "json":
        _write(to_json(ranking), args.out)
    else:
        _write(to_markdown(ranking, args.top, _backend_desc(backend)), args.out)
    _cost_note(backend)


def _job_paths(inputs: list[Path]) -> list[Path]:
    """Job descriptions and/or reviewed requirements files (.json), given as files or folders."""
    kinds = SUPPORTED | {".json"}
    paths = []
    for p in inputs:
        if p.is_dir():
            paths += sorted(q for q in p.iterdir() if q.suffix.lower() in kinds and not q.name.startswith("."))
        else:
            paths.append(p)
    if not paths:
        raise SystemExit("No job descriptions found.")
    stems = [p.stem for p in paths]
    if len(stems) != len(set(stems)):
        raise SystemExit("Two job files share a name (e.g. role.md and role.json); keep one per job.")
    return paths


def cmd_jobs(args, backend, cache):
    from .pipeline import match_jobs
    from .report import jobs_to_json, jobs_to_markdown

    jobs, failed = {}, {}
    for p in _job_paths(args.jobs):
        _progress(f"job      {p.stem}")
        try:
            jobs[p.stem] = load_job_spec(p) if p.suffix.lower() == ".json" else extract_job(p, backend, cache)
        except Exception as e:
            failed[p.stem] = f"{type(e).__name__}: {e}"
    matches = match_jobs(args.resume, jobs, backend, cache=cache, workers=args.workers, progress=_progress)
    matches.errors.update(failed)
    if args.format == "json":
        _write(jobs_to_json(matches), args.out)
    else:
        _write(jobs_to_markdown(matches, args.top, _backend_desc(backend)), args.out)
    _cost_note(backend)


def cmd_fairness(args, backend, cache):
    from .fairness import leak_check, measure_sensitivity

    paths = _resume_paths(args.resumes)
    resumes = {}
    for p in paths:
        try:
            resumes[p.stem] = extract_resume(p, backend, cache).resume
        except Exception as e:
            print(f"skip {p.name}: {e}", file=sys.stderr)

    out = ["# Fairness report", "", "## 1. Leak check (blind profiles across name/pronoun variants)", "",
           "| Candidate | Identical across variants |", "|---|---|"]
    leaks = 0
    for cid, resume in resumes.items():
        rep = leak_check(cid, resume)
        leaks += not rep.identical
        out.append(f"| {cid} | {'yes' if rep.identical else 'NO: ' + rep.diff_example} |")
    out += ["", f"**{len(resumes) - leaks}/{len(resumes)} identical.** Identical blind profiles mean the "
            "scorer receives the same input regardless of the apparent name, gender or ethnicity."]

    if args.measure:
        job = _job(args, backend, cache)
        sample = list(resumes.items())[: args.sample]
        mode = "name shown" if not args.blind_measure else "blind"
        out += ["", f"## 2. Score sensitivity ({mode}, {_backend_desc(backend)})", "",
                "| Candidate | Score range across names | Name std. dev. | Re-score noise range |",
                "|---|---|---|---|"]
        for cid, resume in sample:
            _progress(f"sensitivity {cid}")
            rep = measure_sensitivity(cid, resume, job, backend, repeats=args.repeats, blind=args.blind_measure)
            out.append(f"| {cid} | {min(rep.scores_by_name.values()):.0f}–{max(rep.scores_by_name.values()):.0f} "
                       f"({rep.name_spread:.1f}) | {rep.name_stdev:.1f} | {rep.noise_spread:.1f} |")
        out += ["", "Name spread well above the re-score noise suggests the model reacts to perceived identity, "
                "which is what blinding prevents."]
    _write("\n".join(out) + "\n", args.out)
    _cost_note(backend)
    if leaks:
        sys.exit(1)


def cmd_eval(args, backend, cache):
    import json

    from .evaluate import check_verdicts, eval_report, run_eval

    job_evals, resume_evals = run_eval(args.eval_dir, backend, cache, progress=_progress)
    expected = args.eval_dir / "verdicts.json"
    verdicts = check_verdicts(job_evals, json.loads(expected.read_text())) if expected.exists() else None
    _write(eval_report(job_evals, resume_evals, _backend_desc(backend), verdicts), args.out)
    _cost_note(backend)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="shortlist", description="Evidence-backed, blind resume shortlisting.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--backend", choices=["claude", "local"], default="claude")
    common.add_argument("--model", help="Override the backend's default model")
    common.add_argument("--out", type=Path, help="Write output to a file instead of stdout")
    common.add_argument("--no-cache", action="store_true", help=f"Don't read/write {DEFAULT_CACHE_DIR}/")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("requirements", parents=[common], help="Extract reviewable requirements from a job description")
    p.add_argument("jd", type=Path)
    p.set_defaults(func=cmd_requirements)

    job_args = argparse.ArgumentParser(add_help=False)
    job_args.add_argument("--jd", type=Path, help="Job description file (.md/.txt/.pdf/.docx)")
    job_args.add_argument("--requirements", type=Path, help="Reviewed requirements JSON (overrides --jd)")

    p = sub.add_parser("rank", parents=[common, job_args], help="Rank a folder of resumes against a job")
    p.add_argument("resumes", type=Path, help="Folder of resumes")
    p.add_argument("--top", type=int, default=5, help="Candidates to show in detail")
    p.add_argument("--prefilter-k", type=int, default=25, help="Max candidates sent to the LLM scorer")
    p.add_argument("--workers", type=int, default=4, help="Parallel scoring calls (claude backend)")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.set_defaults(func=cmd_rank)

    p = sub.add_parser("jobs", parents=[common], help="Rank job descriptions by fit for one resume")
    p.add_argument("resume", type=Path, help="The resume (.pdf/.docx/.txt/.md)")
    p.add_argument("jobs", type=Path, nargs="+",
                   help="Job description files or folders; .json files are reviewed requirements")
    p.add_argument("--top", type=int, default=3, help="Jobs to show in detail")
    p.add_argument("--workers", type=int, default=4, help="Parallel scoring calls (claude backend)")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.set_defaults(func=cmd_jobs)

    p = sub.add_parser("fairness", parents=[common, job_args], help="Counterfactual name/pronoun bias tests")
    p.add_argument("resumes", type=Path, help="Folder of resumes")
    p.add_argument("--measure", action="store_true", help="Also measure score sensitivity (costs model calls)")
    p.add_argument("--blind-measure", action="store_true", help="Measure with blinding on instead of names shown")
    p.add_argument("--sample", type=int, default=3, help="Resumes to measure")
    p.add_argument("--repeats", type=int, default=3, help="Re-scores used to estimate noise")
    p.set_defaults(func=cmd_fairness)

    p = sub.add_parser("eval", parents=[common], help="Score ranking quality against graded labels")
    p.add_argument("--eval-dir", type=Path, default=Path("eval"))
    p.set_defaults(func=cmd_eval)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command in ("rank", "jobs") and args.backend == "local":
        args.workers = 1  # one model in memory; parallel calls don't help
    try:
        backend = get_backend(args.backend, args.model)
        cache = Cache(None if args.no_cache else DEFAULT_CACHE_DIR)
        args.func(args, backend, cache)
    except BackendError as e:
        raise SystemExit(f"Error: {e}")
    except ValueError as e:
        raise SystemExit(f"Error: {e}")
    except ImportError as e:
        raise SystemExit(f"Error: {e}")
    except Exception as e:
        # Missing or invalid credentials are the most common first-run problem. The SDK
        # raises TypeError when none are configured, AuthenticationError when rejected.
        if type(e).__name__ == "AuthenticationError" or "Could not resolve authentication" in str(e):
            raise SystemExit("Error: no valid Anthropic API key. Set ANTHROPIC_API_KEY, or use --backend local.")
        raise


if __name__ == "__main__":
    main()
