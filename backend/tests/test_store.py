from app.memory import  store
from  app.db import connect,init_db
import pytest
import sqlite3
import sqlite_vec

def test_upsert_profile_overwrites(tmp_path):
    conn=connect(tmp_path/"t.db")
    init_db(conn)
    store.upsert_profile(conn,"name","三一")
    store.upsert_profile(conn,"name","HIFUMI",confidence=0.9)
    rows= conn.execute("SELECT key,value,confidence FROM profile").fetchall()
    assert len(rows) == 1
    assert  rows[0]["value"]=="HIFUMI"
    assert rows[0]["confidence"]==0.9

def test_list_profile_returns_dicts(tmp_path):
    conn=connect(tmp_path/"t.db")
    init_db(conn)

    assert store.list_profile(conn)==[]#空库

    store.upsert_profile(conn, "job", "学生")
    store.upsert_profile(conn,"name","三一",confidence=0.7)
    store.upsert_profile(conn,"name","三一",confidence=0.9)

    rows=store.list_profile(conn)
    assert isinstance(rows[0],dict)
    assert [r["key"] for r in rows] == ["name","job"]

def test_delete_profile(tmp_path):
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    store.upsert_profile(conn, "name", "三一")
    store.delete_profile(conn,"name")
    store.delete_profile(conn,"不存在的key")
    assert  store.list_profile(conn)==[]

def test_add_event_returns_id_and_limits(tmp_path):
    conn=connect(tmp_path / "t.db")
    init_db(conn)
    id1 = store.add_event(conn,"答辩通过",kind="fact",importance=9)
    id2 = store.add_event(conn,"最近在面试",kind="state",importance=7)
    assert id2>id1
    got1=store.recent_events(conn,1)
    assert  len(got1)==1
    got2=store.recent_events(conn)
    assert  len(got2)==2
    assert  got2[0]["content"]=="最近在面试"
    assert got2[1]["content"] == "答辩通过"
    assert got2[0]["importance"]==7
    assert got2[1]["importance"] == 9

def test_add_event_rejects_bad_kind(tmp_path):
    conn=connect(tmp_path / "t.db")
    init_db(conn)
    with pytest.raises(sqlite3.IntegrityError):
        store.add_event(conn,"随便",kind="瞎写的")
    assert store.recent_events(conn,10)==[]   # 回滚了，一条没留


def test_upsert_profile_refreshes_updated_at(tmp_path):
    """UPDATE 分支必须手写 updated_at——DEFAULT 只在 INSERT 时生效。

    先把时间改成 2000 年，再 upsert 一次；如果 UPDATE 分支漏了 updated_at，
    值会停在 2000 年，这条就红。
    """
    conn = connect(tmp_path / "t.db")
    init_db(conn)

    store.upsert_profile(conn, "name", "三一")
    conn.execute("UPDATE profile SET updated_at='2000-01-01 00:00:00' WHERE key='name'")
    conn.commit()

    store.upsert_profile(conn, "name", "HIFUMI")

    got = conn.execute("SELECT updated_at FROM profile WHERE key='name'").fetchone()
    assert got["updated_at"] > "2000-01-01 00:00:00"


def test_writes_roll_back_on_error(tmp_path):
    """一个 with 块里中途抛异常，之前写的那条不该留在库里。"""
    conn = connect(tmp_path / "t.db")
    init_db(conn)

    with pytest.raises(RuntimeError):
        with conn:
            conn.execute("INSERT INTO profile (key, value) VALUES ('a', '1')")
            raise RuntimeError("中途炸了")

    assert store.list_profile(conn) == []


def test_recent_events_zero_means_empty(tmp_path):
    """边界：n=0 应该返回 0 条。"""
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    store.add_event(conn, "答辩通过", kind="fact")

    assert store.recent_events(conn, 0) == []


def test_add_chunks_is_reimportable(tmp_path):
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    store.init_vec_tables(conn, 4)

    store.add_chunks(conn, "doc1", ["第一段", "第二段", "第三段"],
                     [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]])
    store.add_chunks(conn, "doc1", ["改过的第一段"], [[1, 0, 0, 0]])

    rows = conn.execute(
        "SELECT ordinal, content FROM chunks WHERE doc_id='doc1' ORDER BY ordinal"
    ).fetchall()
    assert [r["content"] for r in rows] == ["改过的第一段"]   # 旧的没残留
    assert rows[0]["ordinal"] == 0


def test_add_chunks_removes_stale_vectors(tmp_path):
    """重导入要连虚表里的旧向量一起清掉。

    漏了这一步，孤儿行会占着 KNN 的 k 名额：KNN 取到孤儿、JOIN 时被甩掉，
    调用方要 2 条只拿到 1 条。
    """
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    store.init_vec_tables(conn, 4)

    store.add_chunks(conn, "doc1", ["苹果", "香蕉"], [[1, 0, 0, 0], [0.9, 0.1, 0, 0]])
    store.add_chunks(conn, "doc1", ["梨"], [[1, 0, 0, 0]])

    assert conn.execute("SELECT count(*) FROM vec_chunks").fetchone()[0] == 1
    got = store.search_chunks(conn, [1, 0, 0, 0], k=2)
    assert [r["content"] for r in got] == ["梨"]


def test_add_chunks_rejects_length_mismatch(tmp_path):
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    store.init_vec_tables(conn, 4)

    with pytest.raises(ValueError):
        store.add_chunks(conn, "doc1", ["甲", "乙"], [[1, 0, 0, 0]])

    assert conn.execute("SELECT count(*) FROM chunks").fetchone()[0] == 0   # 整批回滚


def test_add_chunks_does_not_touch_other_docs(tmp_path):
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    store.init_vec_tables(conn, 4)

    store.add_chunks(conn, "doc1", ["甲的段落"], [[1, 0, 0, 0]])
    store.add_chunks(conn, "doc2", ["乙的段落"], [[0, 1, 0, 0]])
    store.add_chunks(conn, "doc1", ["甲改过了"], [[1, 0, 0, 0]])

    left = conn.execute("SELECT content FROM chunks WHERE doc_id='doc2'").fetchall()
    assert [r["content"] for r in left] == ["乙的段落"]
    assert conn.execute("SELECT count(*) FROM vec_chunks").fetchone()[0] == 2


def test_add_event_writes_vector_only_when_given(tmp_path):
    """embedding=None 时不该往虚表里写东西。"""
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    store.init_vec_tables(conn, 4)

    with_vec = store.add_event(conn, "有向量", kind="fact", embedding=[1, 0, 0, 0])
    store.add_event(conn, "没向量", kind="fact")

    ids = [r[0] for r in conn.execute("SELECT event_id FROM vec_events")]
    assert ids == [with_vec]


def test_init_vec_tables_dim_follows_argument(tmp_path):
    """维度真的跟着参数走，而不是某处写死了 512。"""
    conn = connect(tmp_path / "t.db")
    init_db(conn)

    store.init_vec_tables(conn, 8)
    store.init_vec_tables(conn, 8)          # 幂等，不报错

    ok = sqlite_vec.serialize_float32([0.0] * 8)
    conn.execute("INSERT INTO vec_events (event_id, valid, embedding) VALUES (1, 1, ?)", (ok,))

    bad = sqlite_vec.serialize_float32([0.0] * 9)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO vec_events (event_id, valid, embedding) VALUES (2, 1, ?)", (bad,))


# ---------- search_chunks ----------

def _seed_vec_chunks(conn, dim=4):
    """造 3 个 chunk，走真实写入路径（add_chunks），不手工拼 SQL。"""
    store.init_vec_tables(conn, dim)
    store.add_chunks(
        conn, "doc1", ["苹果", "香蕉", "自行车"],
        [[1.0, 0.0, 0.0, 0.0], [0.9, 0.1, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
    )


def test_search_chunks_nearest_first(tmp_path):
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    _seed_vec_chunks(conn)

    got = store.search_chunks(conn, [1.0, 0.0, 0.0, 0.0], k=2)

    assert [r["content"] for r in got] == ["苹果", "香蕉"]   # 最近的排前面
    assert got[0]["distance"] <= got[1]["distance"]
    assert got[0]["doc_id"] == "doc1"      # JOIN 回表，正文带出来了
    assert got[0]["ordinal"] == 0


def test_search_chunks_k_limits(tmp_path):
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    _seed_vec_chunks(conn)

    assert len(store.search_chunks(conn, [1.0, 0.0, 0.0, 0.0], k=1)) == 1
    assert len(store.search_chunks(conn, [1.0, 0.0, 0.0, 0.0], k=3)) == 3


def test_search_chunks_accepts_plain_list(tmp_path):
    """调用方只给 list[float]，序列化在 store 内部做。"""
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    _seed_vec_chunks(conn)

    got = store.search_chunks(conn, [1.0, 0.0, 0.0, 0.0], k=1)   # 不是 bytes
    assert got[0]["content"] == "苹果"


# ---------- search_events ----------

def _seed_vec_events(conn, dim=4):
    """造 3 条事件，走真实写入路径（add_event）。

    第三条是已失效的状态型记忆。失效要同时写 events.valid_to 和 vec_events.valid，
    只写一处就会和线上不一致——这两行演示的就是那个动作。
    """
    store.init_vec_tables(conn, dim)
    store.add_event(conn, "答辩通过", kind="fact", embedding=[1.0, 0.0, 0.0, 0.0])
    store.add_event(conn, "在准备面试", kind="state", embedding=[0.9, 0.1, 0.0, 0.0])
    stale = store.add_event(conn, "旧状态", kind="state", embedding=[0.0, 0.0, 0.0, 1.0])
    with conn:
        conn.execute("UPDATE events SET valid_to='2020-01-01 00:00:00' WHERE id=?", (stale,))
        conn.execute("UPDATE vec_events SET valid=0 WHERE event_id=?", (stale,))


def test_search_events_skips_stale(tmp_path):
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    _seed_vec_events(conn)

    got = store.search_events(conn, [0.0, 0.0, 0.0, 1.0], k=3)

    assert "旧状态" not in [r["content"] for r in got]   # valid_to 已过的不进结果
    assert len(got) == 2                                 # 结果数受 LIMIT 限


def test_search_events_k_is_after_filter(tmp_path):
    """最近的那条恰好失效时，不该返回空。

    有效性是 vec0 的 metadata 列，过滤发生在 KNN 内部：
    k 就是「要几条有效结果」，不是「只准看几条候选」。
    如果改成「先 KNN 再在 SQL 里过滤」，这条会返回 []。
    """
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    _seed_vec_events(conn)

    got = store.search_events(conn, [0.0, 0.0, 0.0, 1.0], k=1)

    assert len(got) == 1
    assert got[0]["content"] != "旧状态"


def test_search_events_returns_joined_fields(tmp_path):
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    _seed_vec_events(conn)

    got = store.search_events(conn, [1.0, 0.0, 0.0, 0.0], k=1)

    assert got[0]["content"] == "答辩通过"
    assert got[0]["kind"] == "fact"                       # JOIN 回表，字段都在
    assert "distance" in got[0]


def test_search_events_k_larger_than_rows(tmp_path):
    """k 比有效条数大时不报错，返回现有全部。"""
    conn = connect(tmp_path / "t.db")
    init_db(conn)
    _seed_vec_events(conn)

    assert len(store.search_events(conn, [1.0, 0.0, 0.0, 0.0], k=10)) == 2