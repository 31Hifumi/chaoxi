"""测试共用 fixture。

这里只放样板：环境隔离、假 LLM、TestClient。断言全在各自的测试文件里。

约定的两个接口（如果和你想要的不一样，改这里就行，测试文件不用动）：
  1. `app.main.create_app()` 返回 FastAPI 实例
  2. `app.api.chat.get_llm` 是一个 FastAPI 依赖，返回可调用的 LLM 客户端
     测试通过 `app.dependency_overrides` 把它换成假的，全程不联网
"""

import pytest
from fastapi.testclient import TestClient
from app.api.chat import get_llm
from app.db import connect, init_db
from app.main import create_app

class FakeLLM:
    """假 LLM：只记录收到了什么，返回固定回复。不联网、不花钱。"""

    def __init__(self, reply: str = "收到啦"):
        self.reply = reply
        self.calls: list = []

    def __call__(self, messages, *args, **kwargs) -> str:
        assert isinstance(messages, list), f"messages应该是list，收到{type(messages)}"
        self.calls.append(messages)
        return self.reply


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def conn(tmp_path):
    """一个已建好表的空数据库。

    用临时文件而不是 :memory:，因为 WAL 在内存库上不生效，
    而 connect() 会去设 WAL——用文件才能顺便覆盖那条路径。
    """
    c = connect(tmp_path / "test.db")
    init_db(c)
    yield c
    c.close()


@pytest.fixture
def client(tmp_path, monkeypatch, fake_llm):
    """隔离环境起一个测试用的 app。

    注意两个隔离点：
    - 数据库落到 tmp_path，不碰开发用的 chaoxi.db
    - 假 LLM 通过依赖覆盖注入，不走 HTTP，所以不需要 MockTransport
    """
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("CHAOXI_DB", str(tmp_path / "test.db"))

    app = create_app()
    app.dependency_overrides[get_llm] = lambda: fake_llm
    with TestClient(app) as c:
        yield c
