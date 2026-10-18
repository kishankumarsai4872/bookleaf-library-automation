"""
pipeline.py - the main flow (like the original's workflows/intake_pipeline.py):

    message -> classify intent -> run the matching handler -> log it -> reply
"""
import database as db
import routing

HELP_TEXT = (
    "I can help you with:\n"
    "- checking if a book is available (e.g. 'Is Atomic Habits available?')\n"
    "- borrowing a book (e.g. 'I want to borrow The Hobbit')\n"
    "- returning a book (e.g. 'I want to return The Hobbit')\n"
    "- your borrowing history (e.g. 'show my history')\n"
    "- recommendations (e.g. 'recommend a fantasy book')"
)


def _get_member(conn, member_id):
    """Returns (member, error_message). Exactly one of them is None."""
    if member_id is None:
        return None, "Please tell me your member id first."
    member = db.get_member(conn, member_id)
    if member is None:
        return None, f"I couldn't find member id {member_id}."
    return member, None


def _pick_one_book(conn, message):
    """Returns (book, error_message). Exactly one of them is None."""
    books = routing.find_books(message, db.all_books(conn))
    if not books:
        return None, "I couldn't find that book. Please type the full title, e.g. 'Atomic Habits'."
    if len(books) > 1:
        titles = ", ".join(b["title"] for b in books)
        return None, f"I found several books ({titles}). Which one do you mean?"
    return books[0], None


# ---------- one small function per intent ----------
def handle_availability(conn, message):
    books = routing.find_books(message, db.all_books(conn))
    if books:
        lines = []
        for b in books:
            status = "AVAILABLE" if b["available_copies"] > 0 else "NOT available"
            lines.append(f"'{b['title']}' by {b['author']}: {status} "
                         f"({b['available_copies']}/{b['total_copies']} copies)")
        return "\n".join(lines)
    if routing.find_genre(message, db.list_genres(conn)):       # e.g. "do you have any fantasy books?"
        return handle_recommend(conn, message, None)
    return "I couldn't find that book. Please type the full title, e.g. 'Atomic Habits'."


def handle_issue(conn, message, member_id):
    member, error = _get_member(conn, member_id)
    if error:
        return error
    book, error = _pick_one_book(conn, message)
    if error:
        return error
    return db.issue_book(conn, member["id"], book["id"])[1]


def handle_return(conn, message, member_id):
    member, error = _get_member(conn, member_id)
    if error:
        return error
    book, error = _pick_one_book(conn, message)
    if error:
        return error
    return db.return_book(conn, member["id"], book["id"])[1]


def handle_history(conn, member_id):
    member, error = _get_member(conn, member_id)
    if error:
        return error
    rows = db.member_history(conn, member["id"])
    if not rows:
        return "You haven't borrowed any books yet."
    lines = []
    for r in rows:
        status = f"returned on {r['return_date']}" if r["return_date"] else f"due on {r['due_date']}"
        lines.append(f"- {r['title']} (issued {r['issue_date']}, {status})")
    return "Your borrowing history:\n" + "\n".join(lines)


def handle_recommend(conn, message, member_id):
    genres = db.list_genres(conn)
    genre = routing.find_genre(message, genres)
    if genre is None:
        return "Which genre do you like? We have: " + ", ".join(genres)
    recs = db.recommend_by_genre(conn, genre, member_id)
    if not recs:
        return f"Sorry, there are no available {genre} books to suggest right now."
    lines = [f"- {r['title']} by {r['author']} (borrowed {r['times_borrowed']} times)" for r in recs]
    return f"Top {genre} picks for you:\n" + "\n".join(lines)


def handle_escalate(conn, message, member_id):
    task_id = db.create_task(conn, member_id, message)
    return f"I've passed this to a librarian (task #{task_id}). They will contact you within 1 day."


# ---------- the main function ----------
def run_pipeline(conn, message, member_id=None):
    intent = routing.classify_intent(message, db.list_genres(conn))

    if intent == "Escalate":
        reply = handle_escalate(conn, message, member_id)
    elif intent == "Availability":
        reply = handle_availability(conn, message)
    elif intent == "Issue":
        reply = handle_issue(conn, message, member_id)
    elif intent == "Return":
        reply = handle_return(conn, message, member_id)
    elif intent == "History":
        reply = handle_history(conn, member_id)
    elif intent == "Recommend":
        reply = handle_recommend(conn, message, member_id)
    else:
        reply = HELP_TEXT

    db.log_conversation(conn, member_id, message, intent, reply)
    return {"intent": intent, "reply": reply, "member_id": member_id}