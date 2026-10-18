\# BookLeaf Simple



A simplified BookLeaf automation: a FastAPI chatbot for a library. Flow:

message -> FastAPI /message -> keyword router -> handler -> SQLite -> reply (logged).



Features: check book availability, issue/return books with due dates and late fines,

member history, genre recommendations (most borrowed first, skips books already read),

escalation of complaints to a task.



Tech: Python, FastAPI, SQLite, pytest. No LLM or external services.



Run: pip install -r requirements.txt, then `python chat.py` or `uvicorn app:app --reload`.

Test: pytest -v

