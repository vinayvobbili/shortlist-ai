"""An eval where scorings failed is marked INVALID and fails the command, so it can't pass for a real result."""

import pytest

from shortlist_ai import cli, evaluate
from shortlist_ai.evaluate import EvalRun, JobEval, eval_report, failure_banner, scoring_failures
from shortlist_ai.pipeline import Ranking
from shortlist_ai.schema import CandidateResult, JobSpec, Requirement

JOB = JobSpec(title="t", requirements=[Requirement(id="r", description="r", kind="must_have")])
OOM = "RuntimeError: [METAL] Command buffer execution failed: Insufficient Memory"


def result(cid, score):
    return CandidateResult(candidate_id=cid, source_file=f"{cid}.md", score=score, must_haves_met=1,
                           must_haves_total=1, requirements=[], summary="", flags=[])


def run(errors=None):
    ranking = Ranking(JOB, [result("ana", 90), result("ben", 40)], errors=errors or {})
    return EvalRun(None, [JobEval("sre", ranking, [3, 1], [3, 1, 0])], [])


def test_a_clean_run_has_no_banner():
    assert scoring_failures([run()]) == (0, 2, "")
    assert failure_banner([run()]) == []
    assert "INVALID" not in eval_report(run().job_evals, [], "fake")


def test_failures_are_counted_across_runs_and_lead_the_report():
    runs = [run({"cy": OOM}), run({"cy": OOM, "dee": "ValueError: bad"})]
    assert scoring_failures(runs) == (3, 7, f"sre / cy: {OOM}")
    report = eval_report(runs[0].job_evals, [], "fake", banner=failure_banner(runs))
    body = report.split("\n", 2)[2]
    assert body.startswith("> **INVALID RUN: 3 of 7 scorings failed** (first error: sre / cy: RuntimeError")
    assert "not comparable" in body.split("\n")[0]


@pytest.fixture
def eval_cli(tmp_path, monkeypatch):
    def invoke(runs, *flags):
        monkeypatch.setattr(evaluate, "run_eval", lambda *a, **k: runs)
        out = tmp_path / "report.md"
        cli.main(["eval", "--backend", "local", "--no-cache", "--eval-dir", str(tmp_path), "--out", str(out), *flags])
        return out.read_text()
    return invoke


def test_the_command_fails_on_an_invalid_run_but_still_writes_the_report(eval_cli, tmp_path):
    with pytest.raises(SystemExit, match=r"invalid run: 1 of 3 scorings failed .*--allow-failures"):
        eval_cli([run({"cy": OOM})])
    assert "INVALID RUN" in (tmp_path / "report.md").read_text()


def test_allow_failures_accepts_it_and_keeps_the_banner(eval_cli):
    assert "INVALID RUN: 1 of 3" in eval_cli([run({"cy": OOM})], "--allow-failures")


def test_a_clean_run_exits_normally(eval_cli):
    assert "INVALID" not in eval_cli([run()])
