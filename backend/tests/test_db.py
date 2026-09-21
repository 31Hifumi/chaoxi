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


def test_every_connection_can_use_vec0(tmp_path):
    """每个连接都要自带 vec0 扩展。

    `deps.get_conn` 是每请求新建连接，而 sqlite_vec.load 是按连接生效的。
    加载一旦只留在某个连接上（或者忘了 enable_load_extension(True)），
    新建连接碰 vec 表就报 no such module / not authorized。
    """
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    conn.execute(
        "CREATE VIRTUAL TABLE vec_probe USING vec0(id INTEGER PRIMARY KEY, embedding float[4])"
    )
    conn.close()

    fresh = connect(tmp_path / "t.db")     # 全新连接，没手动 load 过扩展
    assert fresh.execute("SELECT count(*) FROM vec_probe").fetchone()[0] == 0