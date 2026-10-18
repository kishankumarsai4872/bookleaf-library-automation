"""Creates the tables and sample data (only if the database is empty)."""
from datetime import date, timedelta
import database as db

BOOKS = [
    ("Atomic Habits", "James Clear", "Self-Help", 2),
    ("Deep Work", "Cal Newport", "Self-Help", 1),
    ("The Alchemist", "Paulo Coelho", "Fiction", 2),
    ("1984", "George Orwell", "Fiction", 1),
    ("Harry Potter and the Philosopher's Stone", "J.K. Rowling", "Fantasy", 3),
    ("The Hobbit", "J.R.R. Tolkien", "Fantasy", 1),
    ("Sapiens", "Yuval Noah Harari", "History", 2),
    ("The Silk Roads", "Peter Frankopan", "History", 1),
    ("Clean Code", "Robert C. Martin", "Technology", 2),
    ("Hands-On Machine Learning", "Aurelien Geron", "Technology", 1),
    ("Gone Girl", "Gillian Flynn", "Thriller", 1),
    ("The Girl with the Dragon Tattoo", "Stieg Larsson", "Thriller", 2),
]
MEMBERS = [("Ravi Kumar", "ravi@example.com"), ("Anita Rao", "anita@example.com"),
           ("Kishan", "kishan@example.com")]


def seed():
    conn = db.connect()
    db.create_tables(conn)
    if conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] > 0:
        conn.close()
        return
    for title, author, genre, copies in BOOKS:
        db.add_book(conn, title, author, genre, copies)
    for name, email in MEMBERS:
        db.add_member(conn, name, email)

    # A little past history so recommendations have something to rank by.
    long_ago = date.today() - timedelta(days=30)
    for member_id, book_id in [(1, 1), (2, 1), (2, 6)]:          # Ravi: Atomic Habits; Anita: Atomic Habits, Hobbit
        db.issue_book(conn, member_id, book_id, today=long_ago)
        db.return_book(conn, member_id, book_id, today=long_ago + timedelta(days=10))
    db.issue_book(conn, 2, 7, today=date.today() - timedelta(days=5))   # Anita currently has Sapiens
    conn.close()
    print(f"Seeded {len(BOOKS)} books and {len(MEMBERS)} members.")


if __name__ == "__main__":
    seed()