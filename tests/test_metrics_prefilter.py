import math

from shortlist_ai.evaluate import (
    EvalRun,
    JobEval,
    check_verdicts,
    eval_report,
    ndcg_at_k,
    precision_at_k,
    resume_evals,
    stability_report,
)
from shortlist_ai.pipeline import Ranking
from shortlist_ai.prefilter import bm25_rank
from shortlist_ai.schema import CandidateResult, JobSpec, Requirement, ScoredRequirement
from shortlist_ai.score import shuffle_requirements


def test_ndcg():
    grades = [3, 2, 1, 0]
    assert ndcg_at_k([3, 2, 1, 0], grades, 3) == 1.0
    assert ndcg_at_k([0, 1, 2, 3], grades, 3) < 0.3
    swapped = ndcg_at_k([2, 3, 1, 0], grades, 3)
    assert 0.8 < swapped < 1.0
    assert math.isclose(ndcg_at_k([0, 0], [0, 0], 2), 1.0)  # nothing relevant: trivially ideal


def test_precision_at_k():
    assert precision_at_k([3, 1, 2], 3) == 2 / 3
    assert precision_at_k([], 3) == 0.0


def test_bm25_prefers_matching_profiles():
    docs = {
        "gcp": "BigQuery Dataflow Airflow Python pipelines",
        "aws": "Redshift Glue Airflow Python pipelines",
        "nurse": "ICU critical care patient education",
    }
    ranked = [d for d, _ in bm25_rank("BigQuery Dataflow Airflow Python", docs)]
    assert ranked == ["gcp", "aws", "nurse"]


def _result(cid, score, met=1, total=1):
    return CandidateResult(candidate_id=cid, source_file=f"{cid}.md", score=score, must_haves_met=met,
                           must_haves_total=total, requirements=[], summary="", flags=[])


def test_resume_evals_read_the_matrix_per_resume():
    job = JobSpec(title="t", requirements=[Requirement(id="r", description="r", kind="must_have")])
    evals = [JobEval("de", Ranking(job, [_result("oli", 90), _result("sam", 20)]), [], []),
             JobEval("da", Ranking(job, [_result("sam", 80), _result("oli", 95)]), [], []),
             JobEval("fe", Ranking(job, [_result("oli", 10), _result("sam", 10), _result("cook", 5)]), [], [])]
    labels = {"de": {"oli": 3, "sam": 1}, "da": {"oli": 1, "sam": 3}, "fe": {}}
    by = {r.resume: r for r in resume_evals(evals, labels)}
    assert set(by) == {"oli", "sam"}                                # cook fits nothing: skipped
    assert [j for j, _ in by["oli"].ranked_jobs] == ["da", "de", "fe"]
    assert by["oli"].metrics()["top1"] == 0.0                       # picked da (1) over de (3)
    assert by["sam"].metrics() == {"ndcg@3": 1.0, "top1": 1.0}


def test_check_verdicts_separates_lenient_from_strict():
    job = JobSpec(title="t", requirements=[Requirement(id="r", description="r", kind="must_have")])

    def result(cid, **verdicts):
        r = _result(cid, 50)
        r.requirements = [ScoredRequirement(requirement_id=k, verdict=v, evidence=[], reasoning="", kind="must_have",
                                            evidence_verified=True) for k, v in verdicts.items()]
        return r

    evals = [JobEval("sre", Ranking(job, [result("cert", k8s="met", py="met"), result("real", k8s="partial")]), [], [])]
    expected = {"sre": {"cert": {"k8s": "partial", "py": "met"}, "real": {"k8s": "met"}, "gone": {"k8s": "met"}}}
    outcomes = {(v.resume, v.requirement): v.outcome for v in check_verdicts(evals, expected)}
    assert outcomes == {("cert", "k8s"): "too lenient", ("cert", "py"): "agree",
                        ("real", "k8s"): "too strict", ("gone", "k8s"): "missing"}
    assert "**1/4 agree** · 1 too lenient · 1 too strict · 1 missing" in eval_report(evals, [], "fake",
                                                                                   check_verdicts(evals, expected))


def test_shuffle_requirements_is_seeded_and_keeps_the_set():
    job = JobSpec(title="t", requirements=[Requirement(id=f"r{i}", description="d", kind="must_have")
                                           for i in range(6)])
    a, b = shuffle_requirements(job, 1), shuffle_requirements(job, 1)
    assert [r.id for r in a.requirements] == [r.id for r in b.requirements]
    assert [r.id for r in a.requirements] != [r.id for r in job.requirements]
    assert sorted(r.id for r in a.requirements) == [r.id for r in job.requirements]


def test_stability_report_counts_verdicts_that_move():
    job = JobSpec(title="t", requirements=[Requirement(id="r", description="r", kind="must_have")])

    def run(seed, k8s, score):
        r = _result("cand", score)
        r.requirements = [ScoredRequirement(requirement_id=q, verdict=v, evidence=[], reasoning="",
                                            kind="must_have", evidence_verified=True)
                          for q, v in (("k8s", k8s), ("py", "met"))]
        return EvalRun(seed, [JobEval("sre", Ranking(job, [r]), [3], [3])], [])

    runs = [run(None, "met", 100), run(1, "partial", 75), run(2, "met", 100)]
    text = "\n".join(stability_report(runs, {"sre": {"cand": {"k8s": "met"}}}))
    assert "Stability across 3 requirement orderings" in text
    assert "1 of 2 requirement verdicts (50%) were identical" in text
    assert "| sre | cand | `k8s` | met → partial → met |" in text
    assert "| Expected verdicts agreeing (of 1) | 0.0 | 0.7 | 1.0 |" in text
    assert "at most 25.0" in text
