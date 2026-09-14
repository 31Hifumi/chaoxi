from app.api import chat

from app.db import session as store


def test_chat_creates_session_and_returns_reply(client,fake_llm):
    r = client.post("/api/chat",json={"session_id":None,"message":"在吗"})
    assert r.status_code==200
    body = r.json()
    assert body["reply"] == fake_llm.reply
    assert isinstance(body["session_id"],int)

def test_chat_passes_message_to_llm(client,fake_llm):
    client.post("/api/chat",json={"session_id":None,"message":"在吗"})
    assert fake_llm.calls == [[{"role":"user","content":"在吗"}]]


# ────────────────────── 会话不存在要说出来（不是悄悄新建） ──────────────────────


def test_chat_rejects_unknown_session_id(client):
    """给一个不存在的 id 必须报错。

    悄悄新建的话，调用方拿着自己传的旧 id 继续发，永远不知道自己接错了会话——
    这种静默失败比报错难查一百倍。
    """
    r = client.post("/api/chat", json={"session_id": 99999, "message": "在吗"})
    assert r.status_code == 404


def test_chat_keeps_existing_session_id(client, conn):
    """带着已有会话发消息，要续在那个会话上，不能新建。"""
    sid = store.create_session(conn, "旧会话")

    r = client.post("/api/chat", json={"session_id": sid, "message": "接着说"})

    assert r.status_code == 200
    assert r.json()["session_id"] == sid
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1


def test_rejected_session_leaves_nothing_behind(client, conn):
    """被拒绝的那一次不能留下半条痕迹。

    这条锁的是顺序：404 的判断必须发生在任何写入之前。
    """
    client.post("/api/chat", json={"session_id": 99999, "message": "在吗"})

    assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


# ────────────────────────── 两条消息都要落库 ──────────────────────────


def test_chat_persists_user_and_assistant_messages(client, conn, fake_llm):
    """user 和 assistant 各存一条，顺序不能反。

    只断言「有内容」挡不住顺序写反——那样模型下一轮读到的历史就是倒的。
    """
    r = client.post("/api/chat", json={"session_id": None, "message": "在吗"})
    sid = r.json()["session_id"]

    assert store.get_messages(conn, sid) == [
        {"role": "user", "content": "在吗"},
        {"role": "assistant", "content": fake_llm.reply},
    ]


def test_chat_appends_to_existing_session_history(client, conn, fake_llm):
    """续聊是往后追加，历史不丢也不覆盖。"""
    sid = store.create_session(conn, "旧会话")

    client.post("/api/chat", json={"session_id": sid, "message": "第一句"})
    client.post("/api/chat", json={"session_id": sid, "message": "第二句"})

    rows = store.get_messages(conn, sid)
    assert [m["role"] for m in rows] == ["user", "assistant", "user", "assistant"]
    assert rows[2]["content"] == "第二句"


# ────────────────────────── 入参校验 ──────────────────────────


def test_chat_rejects_blank_message(client):
    """只有空白的 message 不该发到模型那儿去。"""
    r = client.post("/api/chat", json={"session_id": None, "message": "   "})
    assert r.status_code == 422

