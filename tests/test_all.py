from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

import database as db
import pipeline
import routing


@pytest.fixture
def conn():
    c = db.connect(":memory:")          # temporary DB, nothing written to disk
    db.create_tables(c)
    db.add_book(c, "Dune", "Frank Herbert", "Sci-Fi", 1)
    db.add_book(c, "Emma", "Jane Austen", "Romance", 1)
    db.add_book(c, "Persuasion", "Jane Austen", "Romance", 1)
    db.add_member(c, "Asha", "asha@example.com")
    db.add_member(c, "Bala", "bala@example.com")
    return c


def test_router_intents():
    g = ["Fantasy"]
    assert routing.classify_intent("Is Dune available?", g) == "Availability"
    assert routing.classify_intent("I want to borrow Dune", g) == "Issue"
    assert routing.classify_intent("returning Dune", g) == "Return"
    assert routing.classify_intent("recommend something", g) == "Recommend"
    assert routing.classify_intent("fantasy", g) == "Recommend"
    assert routing.classify_intent("I want a refund NOW", g) == "Escalate"
    assert routing.classify_intent("blah blah", g) == "Unknown"


def test_escalation_beats_other_rules():
    assert routing.classify_intent("I want to return this, I am angry", []) == "Escalate"


def test_availability_reply(conn):
    reply = pipeline.run_pipeline(conn, "Is Dune available?")["reply"]
    assert "AVAILABLE" in reply and "NOT" not in reply


def test_issue_then_not_available(conn):
    pipeline.run_pipeline(conn, "I want to borrow Dune", member_id=1)
    reply = pipeline.run_pipeline(conn, "Is Dune available?")["reply"]
    assert "NOT available" in reply
    assert "no copies" in pipeline.run_pipeline(conn, "borrow Dune", member_id=2)["reply"]


def test_issue_needs_member(conn):
    assert "member id" in pipeline.run_pipeline(conn, "borrow Dune")["reply"]


def test_late_return_fine(conn):
    db.issue_book(conn, 1, 1, today=date.today() - timedelta(days=20))
    ok, msg = db.return_book(conn, 1, 1)
    assert ok and f"Rs {6 * db.FINE_PER_DAY}" in msg        # 20 days - 14 allowed = 6 late


def test_history(conn):
    pipeline.run_pipeline(conn, "borrow Dune", member_id=1)
    assert "Dune" in pipeline.run_pipeline(conn, "show my history", member_id=1)["reply"]


def test_recommend_skips_already_read(conn):
    db.issue_book(conn, 1, 2)
    db.return_book(conn, 1, 2)                       # Asha has read Emma
    titles = [r["title"] for r in db.recommend_by_genre(conn, "romance", member_id=1)]
    assert titles == ["Persuasion"]


def test_recommend_most_popular_first(conn):
    db.issue_book(conn, 2, 3)
    db.return_book(conn, 2, 3)                       # Persuasion borrowed once
    titles = [r["title"] for r in db.recommend_by_genre(conn, "Romance")]
    assert titles[0] == "Persuasion"


def test_escalation_creates_task_and_log(conn):
    out = pipeline.run_pipeline(conn, "I want to speak to a manager", member_id=1)
    assert out["intent"] == "Escalate"
    assert len(db.list_tasks(conn)) == 1
    assert conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] == 1


def test_api(tmp_path, monkeypatch):
    monkeypatch.setenv("BOOKLEAF_DB", str(tmp_path / "test.db"))
    from app import app
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        r = client.post("/message", json={"message": "Is The Hobbit available?"})
        assert r.json()["intent"] == "Availability"
        assert client.post("/message", json={"message": ""}).status_code == 422