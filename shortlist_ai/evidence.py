"""Checking that an evidence quote really is in the text it claims to come from.

Used by the scorer (quotes from the whole profile) and by the years check (quotes from one role).
"""

import re


def _norm(text: str) -> str:
    text = text.lower().replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    return " ".join(re.sub(r"[^\w%$+#.'/-]+", " ", text).split())


def _in_labeled_line(quote: str, profile: str) -> bool:
    """A labeled list quoted with some items left out ("Skills: Python" from "Skills: SQL, Python,
    Excel"): true if one profile line has that label and every quoted item, as whole words."""
    label, sep, items = quote.partition(":")
    items = [_norm(i) for i in re.split(r",|\.{3}|…", items) if _norm(i)]
    if not sep or not _norm(label) or not items:
        return False
    for line in profile.splitlines():
        line_label, line_sep, values = line.strip().lstrip("-* ").partition(":")
        if line_sep and _norm(line_label) == _norm(label):
            padded = f" {_norm(values)} "
            if all(f" {i} " in padded for i in items):
                return True
    return False


def quote_in_profile(quote: str, profile: str) -> bool:
    """True if the quote appears in the profile, ignoring case, whitespace and most
    punctuation. Quotes elided with '...' must have every fragment present, and a labeled
    list may leave items out."""
    haystack = _norm(profile)
    fragments = [f for f in re.split(r"\.{3}|…", quote) if _norm(f)]
    return bool(fragments) and (all(_norm(f) in haystack for f in fragments) or _in_labeled_line(quote, profile))
