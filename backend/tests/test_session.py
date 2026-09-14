"""session.py 的测试：会话与消息的读写。

这个文件里的用例不验证「代码写得对不对」，它验证的是「SQL 写对了没有」。
SQL 是字符串形式的代码，写错了不会在导入时报错，只会静默地不干活，
所以这里的每一条都是必要的。
"""

import sqlite3

import pytest

from app.db import session as store


# ────────────────────────── create_session ──────────────────────────


def test_create_session_returns_int_id(conn):
    sid = store.create_session(conn, "第一次对话")
    assert isinstance(sid, int)


def test_create_session_returns_distinct_ids(conn):
    first = store.create_session(conn, "甲")
    second = store.create_session(conn, "乙")
    assert first != second


def test_created_session_is_persisted(conn):
    sid = store.create_session(conn, "存进去了吗")
    row = store.get_session(conn, sid)
    assert row is not None
    assert row["title"] == "存进去了吗"


# ────────────────────────── get_session ──────────────────────────


def test_get_session_returns_none_when_missing(conn):
    assert store.get_session(conn, 99999) is None


def test_get_session_returns_id_and_title(conn):
    sid = store.create_session(conn, "标题")
    row = store.get_session(conn, sid)
    assert row["id"] == sid
    assert row["title"] == "标题"


# ────────────────────────── add_message ──────────────────────────


def test_add_message_returns_int_id(conn):
    sid = store.create_session(conn, "s")
    mid = store.add_message(conn, sid, "user", "你好")
    assert isinstance(mid, int)


def test_add_message_persists_role_and_content(conn):
    sid = store.create_session(conn, "s")
    store.add_message(conn, sid, "user", "你好")

    rows = store.get_messages(conn, sid)
    assert len(rows) == 1
    assert rows[0]["role"] == "user"
    assert rows[0]["content"] == "你好"


def test_add_message_rejects_unknown_session(conn):
    """外键约束必须真的开着。PRAGMA 漏了的话这条会静默通过，孤儿消息就进库了。"""
    with pytest.raises(sqlite3.IntegrityError):
        store.add_message(conn, 99999, "user", "孤儿消息")


def test_add_message_rejects_invalid_role(conn):
    """schema 里那条 CHECK 约束得真生效——写进去非法角色，后面渲染就会崩。"""
    sid = store.create_session(conn, "s")
    with pytest.raises(sqlite3.IntegrityError):
        store.add_message(conn, sid, "robot", "角色不合法")


# ────────────────────────── get_messages ──────────────────────────


def test_get_messages_is_ordered_by_id(conn):
    sid = store.create_session(conn, "s")
    for text in ("一", "二", "三"):
        store.add_message(conn, sid, "user", text)

    assert [r["content"] for r in store.get_messages(conn, sid)] == ["一", "二", "三"]


def test_get_messages_only_returns_given_session(conn):
    """会话隔离。漏掉 WHERE 的话，甲的对话里会混进乙的消息——而且不报错。"""
    a = store.create_session(conn, "甲")
    b = store.create_session(conn, "乙")
    store.add_message(conn, a, "user", "属于甲")
    store.add_message(conn, b, "user", "属于乙")

    assert [r["content"] for r in store.get_messages(conn, a)] == ["属于甲"]


def test_get_messages_returns_empty_list_for_empty_session(conn):
    sid = store.create_session(conn, "空会话")
    assert store.get_messages(conn, sid) == []


# ────────────────────────── 级联删除 ──────────────────────────


def test_deleting_session_removes_its_messages(conn):
    """schema 里写了 ON DELETE CASCADE，但外键默认是关的，不验就不知道它到底生效没。"""
    sid = store.create_session(conn, "s")
    store.add_message(conn, sid, "user", "会跟着消失")

    conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))
    conn.commit()

    assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0
