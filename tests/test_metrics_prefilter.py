import math

from shortlist_ai.evaluate import JobEval, ndcg_at_k, precision_at_k, resume_evals
from shortlist_ai.pipeline import Ranking
from shortlist_ai.schema import CandidateResult, JobSpec, Requirement
from shortlist_ai.prefilter import bm25_rank


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
