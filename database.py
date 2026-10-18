"""database.py - SQLite tables and every function that reads or writes data."""
import os
import sqlite3
from datetime import date, datetime, timedelta

LOAN_DAYS = 14      # how long a member may keep a book
FINE_PER_DAY = 2    # late fine in rupees per day


def connect(db_file=None):
    """Open the database. Path comes from env var BOOKLEAF_DB (default bookleaf.db)."""
    db_file = db_file or os.environ.get("BOOKLEAF_DB", "bookleaf.db")
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row      # read columns by name: row["title"]
    return conn


def create_tables(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, author TEXT NOT NULL, genre TEXT NOT NULL,
        total_copies INTEGER NOT NULL, available_copies INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, email TEXT UNIQUE NOT NULL
    );
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL REFERENCES books(id),
        member_id INTEGER NOT NULL REFERENCES members(id),
        issue_date TEXT NOT NULL, due_date TEXT NOT NULL,
        return_date TEXT                       -- NULL = still borrowed
    );
    CREATE TABLE IF NOT EXISTS conversations (  -- every message + reply
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER, message TEXT NOT NULL, intent TEXT NOT NULL,
        reply TEXT NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tasks (          -- escalations for a human
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER, message TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open', due_date TEXT NOT NULL, created_at TEXT NOT NULL
    );
    """)
    conn.commit()


# ---------- adding / reading basic data ----------
def add_book(conn, title, author, genre, copies=1):
    cur = conn.execute(
        "INSERT INTO books (title, author, genre, total_copies, available_copies) VALUES (?,?,?,?,?)",
        (title, author, genre, copies, copies))
    conn.commit()
    return cur.lastrowid


def add_member(conn, name, email):
    cur = conn.execute("INSERT INTO members (name, email) VALUES (?,?)", (name, email))
    conn.commit()
    return cur.lastrowid


def get_member(conn, member_id):
    return conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()


def all_books(conn):
    return conn.execute("SELECT * FROM books ORDER BY title").fetchall()


def list_genres(conn):
    rows = conn.execute("SELECT DISTINCT genre FROM books ORDER BY genre").fetchall()
    return [r["genre"] for r in rows]

# ---------- issue / return ----------
def issue_book(conn, member_id, book_id, today=None):
    """Returns (ok, message)."""
    today = today or date.today()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    member = get_member(conn, member_id)
    if book is None:
        return False, "Book not found."
    if member is None:
        return False, "Member not found."
    if book["available_copies"] <= 0:
        return False, f"Sorry, '{book['title']}' has no copies available right now."
    already = conn.execute(
        "SELECT 1 FROM transactions WHERE book_id=? AND member_id=? AND return_date IS NULL",
        (book_id, member_id)).fetchone()
    if already:
        return False, f"You already have '{book['title']}'."

    due = today + timedelta(days=LOAN_DAYS)
    conn.execute(
        "INSERT INTO transactions (book_id, member_id, issue_date, due_date) VALUES (?,?,?,?)",
        (book_id, member_id, today.isoformat(), due.isoformat()))
    conn.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = ?", (book_id,))
    conn.commit()
    return True, f"Issued '{book['title']}' to {member['name']}. Due on {due.isoformat()}."


def return_book(conn, member_id, book_id, today=None):
    """Returns (ok, message). Message includes the fine if the book is late."""
    today = today or date.today()
    txn = conn.execute(
        "SELECT * FROM transactions WHERE book_id=? AND member_id=? AND return_date IS NULL",
        (book_id, member_id)).fetchone()
    if txn is None:
        return False, "I couldn't find an active loan of that book for you."

    conn.execute("UPDATE transactions SET return_date = ? WHERE id = ?", (today.isoformat(), txn["id"]))
    conn.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = ?", (book_id,))
    conn.commit()

    days_late = (today - date.fromisoformat(txn["due_date"])).days
    if days_late > 0:
        return True, f"Returned {days_late} day(s) late. Fine: Rs {days_late * FINE_PER_DAY}."
    return True, "Thanks, the book was returned on time."


def member_history(conn, member_id):
    return conn.execute(
        """SELECT b.title, t.issue_date, t.due_date, t.return_date
           FROM transactions t JOIN books b ON b.id = t.book_id
           WHERE t.member_id = ? ORDER BY t.issue_date DESC""", (member_id,)).fetchall()

# ---------- genre recommendation ----------
def recommend_by_genre(conn, genre, member_id=None, limit=3):
    """In-stock books of this genre, most borrowed first; skips books this member already borrowed."""
    query = """
        SELECT b.*, COUNT(t.id) AS times_borrowed
        FROM books b LEFT JOIN transactions t ON t.book_id = b.id
        WHERE LOWER(b.genre) = LOWER(?) AND b.available_copies > 0
    """
    params = [genre]
    if member_id is not None:
        query += " AND b.id NOT IN (SELECT book_id FROM transactions WHERE member_id = ?)"
        params.append(member_id)
    query += " GROUP BY b.id ORDER BY times_borrowed DESC, b.title LIMIT ?"
    params.append(limit)
    return conn.execute(query, params).fetchall()


# ---------- logging + escalation ----------
def _now():
    return datetime.now().isoformat(timespec="seconds")


def log_conversation(conn, member_id, message, intent, reply):
    conn.execute(
        "INSERT INTO conversations (member_id, message, intent, reply, created_at) VALUES (?,?,?,?,?)",
        (member_id, message, intent, reply, _now()))
    conn.commit()


def create_task(conn, member_id, message):
    due = (date.today() + timedelta(days=1)).isoformat()
    cur = conn.execute(
        "INSERT INTO tasks (member_id, message, due_date, created_at) VALUES (?,?,?,?)",
        (member_id, message, due, _now()))
    conn.commit()
    return cur.lastrowid


def list_tasks(conn):
    return conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()