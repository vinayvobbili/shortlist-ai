"""Cheap first pass for large pools: rank blind profiles by BM25 keyword relevance to
the requirements, and send only the top K to the (slower, costlier) LLM scorer.

Lexical, so it misses synonyms ("k8s" vs "Kubernetes"); keep K generous. It only
decides who gets a closer look, never who is rejected outright - everyone below
the cut is listed in the report as not assessed.
"""

import math
import re
from collections import Counter

_STOP = set("""a an and are as at be by for from has have in is it its of on or that the to
with will you your we our this must should experience years year strong ability""".split())


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9+#.]+", text.lower()) if t not in _STOP and len(t) > 1]


def bm25_rank(query: str, documents: dict[str, str], k1: float = 1.5, b: float = 0.75) -> list[tuple[str, float]]:
    docs = {doc_id: tokenize(text) for doc_id, text in documents.items()}
    if not docs:
        return []
    avg_len = sum(len(t) for t in docs.values()) / len(docs) or 1.0
    df = Counter(term for tokens in docs.values() for term in set(tokens))
    n = len(docs)
    q_terms = set(tokenize(query))

    scores = {}
    for doc_id, tokens in docs.items():
        tf = Counter(tokens)
        score = 0.0
        for term in q_terms:
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * tf[term] * (k1 + 1) / (tf[term] + k1 * (1 - b + b * len(tokens) / avg_len))
        scores[doc_id] = score
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
