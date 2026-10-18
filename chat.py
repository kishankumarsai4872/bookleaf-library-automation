"""Terminal chat - test the bot without starting the web server. Run: python chat.py"""
import database as db
import pipeline
from seed import seed


def main():
    seed()
    conn = db.connect()
    raw = input("Your member id (1=Ravi, 2=Anita, 3=Kishan, or press Enter to skip): ").strip()
    member_id = int(raw) if raw.isdigit() else None
    print("Type a message ('quit' to exit). Try: 'Is The Hobbit available?'\n")
    while True:
        text = input("You: ").strip()
        if text.lower() in ("quit", "exit"):
            break
        if text:
            result = pipeline.run_pipeline(conn, text, member_id)
            print(f"[intent: {result['intent']}]\nBot: {result['reply']}\n")


if __name__ == "__main__":
    main()