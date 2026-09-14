import json

import httpx
import pytest

from app.config import Settings
from app.llm import chat


def make_settings(tmp_path):
    return Settings("sk-test", "https://api.deepseek.com", "deepseek-flash",
                    tmp_path / "t.db")


def make_client(handler):
    """把假服务器包成一个真的 httpx.Client，直接注入给 chat。"""
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_chat_returns_content(tmp_path):
    def handler(request):
        assert request.headers["authorization"] == "Bearer sk-test"
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "你好呀"}}],
        })

    out = chat([{"role": "user", "content": "在吗"}], make_settings(tmp_path),
               client=make_client(handler))
    assert out == "你好呀"


def test_chat_raises_on_http_error(tmp_path):
    def handler(request):
        return httpx.Response(500, json={"error": "boom"})

    with pytest.raises(httpx.HTTPStatusError):
        chat([{"role": "user", "content": "在吗"}], make_settings(tmp_path),
             client=make_client(handler))


def test_chat_json_mode_sends_response_format(tmp_path):
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "{}"}}],
        })

    chat([{"role": "user", "content": "输出 JSON"}], make_settings(tmp_path),
         json_mode=True, client=make_client(handler))

    assert seen["response_format"] == {"type": "json_object"}
    assert seen["model"] == "deepseek-flash"


def test_chat_without_json_mode_omits_response_format(tmp_path):
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "好"}}],
        })

    chat([{"role": "user", "content": "在吗"}], make_settings(tmp_path),
         client=make_client(handler))

    assert "response_format" not in seen
