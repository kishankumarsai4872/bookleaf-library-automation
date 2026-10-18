"""
routing.py - decides WHAT the user wants (the "intent") and pulls out
the book title / genre from the message.

Same idea as the original's workflows/routing.py, but only the first,
fastest layer: keyword rules. First rule that matches wins, so ORDER MATTERS.
"""
import re

# (intent, pattern). Escalation is first so a complaint is never treated as a normal request.
RULES = [
    ("Escalate",     r"\b(urgent|complaint|refund|angry|human|manager|legal|fraud)\b"),
    ("Return",       r"\b(return|returning|returned|give back)\b"),
    ("Recommend",    r"\b(recommend|suggest|suggestion)\b"),
    ("Availability", r"\b(available|availability|in stock|do you have|have you got|is there|copies)\b"),
    ("Issue",        r"\b(borrow|issue|check ?out|take)\b"),
    ("History",      r"\b(history|my books|borrowed|what did i)\b"),
    ("Recommend",    r"\b(want to read|something to read|looking for a)\b"),
]
RULES = [(intent, re.compile(p, re.IGNORECASE)) for intent, p in RULES]


def classify_intent(message, genres=()):
    """Return one of: Escalate, Return, Recommend, Availability, Issue, History, Unknown."""
    for intent, pattern in RULES:
        if pattern.search(message):
            return intent
    # No keyword matched, but if they just typed a genre name ("fantasy"), treat it as a recommendation request.
    lower = message.lower()
    if any(g.lower() in lower for g in genres):
        return "Recommend"
    return "Unknown"


def find_genre(message, genres):
    """Return the genre (as stored in the DB) mentioned in the message, or None."""
    lower = message.lower()
    for g in genres:
        if g.lower() in lower:
            return g
    return None


def find_books(message, books):
    """Books whose full title appears in the message; if none, books whose author appears."""
    lower = message.lower()
    by_title = [b for b in books if b["title"].lower() in lower]
    if by_title:
        return by_title
    return [b for b in books if b["author"].lower() in lower]