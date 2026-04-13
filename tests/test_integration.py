import pytest
import os
from db import Database

@pytest.fixture
def test_db():
    db = Database(db_name="test.db")
    db.init_table()

    conn = db._get_connection()
    try:
        conn.execute("DELETE FROM users")
        conn.commit()
    finally:
        conn.close()

    yield db
    if os.path.exists("test.db"):
        os.remove("test.db")

def test_save_and_get_score(test_db):
    test_db.save_score("Name1", 5)

    results = test_db.get_all_scores()

    assert len(results) == 1
    assert results[0]["login"] == "Name1"
    assert results[0]["score"] == 5