from app.db import connect, init_db


def test_init_db_creates_tables(tmp_path):
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    names = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"sessions", "messages"} <= names


def test_init_db_is_idempotent(tmp_path):
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    init_db(conn)          # 再跑一次不应该抛错
    conn.close()


def test_wal_mode_enabled(tmp_path):
    conn = connect(tmp_path / "t.db")
    assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"