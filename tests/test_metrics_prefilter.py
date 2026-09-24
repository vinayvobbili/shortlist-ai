import math

from shortlist_ai.evaluate import ndcg_at_k, precision_at_k
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
