"""应用启动时的装配。

盯的是 lifespan：建表、按配置建向量表。这些只有「起一个 app」才验得到，
单元测试碰不着——测试自己会调 init_vec_tables，正好把「应用里没人调」遮住。
"""

import sqlite_vec
from fastapi.testclient import TestClient

from app.api.chat import get_llm
from app.db import connect
from app.main import create_app


def test_startup_creates_vec_tables(client):
    """向量表要在启动时就建好。

    漏了那句不会当场报错——要等第一次检索才 no such table，
    那时离故障现场已经很远。这条测试就是那个「当场」。
    """
    conn = connect(client.app.state.settings.db_path)
    try:
        names = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vec_%'")}
    finally:
        conn.close()

    # vec0 自己还会建一堆影子表（vec_events_info / vec_events_chunks ...），
    # 所以只断言两张主表在，不管它们带出来的家属
    assert {"vec_events", "vec_chunks"} <= names


def test_startup_uses_configured_embed_dim(tmp_path, monkeypatch):
    """建向量表用的维度必须来自 EMBED_DIM，不能是写死的默认值。

    故意配 8 维：代码里要是写死了 512，插 8 维向量会报维度不符。
    """
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("CHAOXI_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("EMBED_DIM", "8")

    app = create_app()
    app.dependency_overrides[get_llm] = lambda: (lambda *a, **kw: "x")
    with TestClient(app):
        pass

    conn = connect(tmp_path / "t.db")
    try:
        vec = sqlite_vec.serialize_float32([0.0] * 8)
        conn.execute(
            "INSERT INTO vec_events (event_id, valid, embedding) VALUES (1, 1, ?)",
            (vec,),
        )
    finally:
        conn.close()
