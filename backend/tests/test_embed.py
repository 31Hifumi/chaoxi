"""嵌入：契约与边界。

全程用假实现——真模型要下 100MB，不该进单元测试。
"维度跟配置对不对得上"那条得跑真模型，见文件末尾，默认跳过。
"""

import os

import pytest

from app.config import Settings
from app.memory import embed as embed_mod


class FakeModel:
    """假嵌入模型：固定维度、记录调用，不下载任何东西。"""

    def __init__(self, dim=4):
        self.dim = dim
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[0.5] * self.dim for _ in texts]


@pytest.fixture
def settings(tmp_path):
    return Settings(
        deepseek_api_key="sk-test",
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-flash",
        db_path=tmp_path / "t.db",
    )


def test_one_vector_per_text(settings):
    out = embed_mod.embed(["你好", "世界"], settings, model=FakeModel(dim=4))
    assert len(out) == 2
    assert all(len(v) == 4 for v in out)


def test_preserves_input_order(settings):
    """顺序不能乱——向量和文本错位了，检索出来的是别人的记忆。"""
    model = FakeModel()
    embed_mod.embed(["第一", "第二", "第三"], settings, model=model)
    assert model.calls == [["第一", "第二", "第三"]]


def test_empty_input_returns_empty_without_touching_model(settings):
    """空输入直接返回，一次都不该调模型（真模型加载要下 100MB）。"""
    model = FakeModel()
    assert embed_mod.embed([], settings, model=model) == []
    assert model.calls == []


def test_dim_comes_from_model_not_hardcoded(settings):
    """维度跟着模型走，代码里不许写死某个数字。"""
    small = embed_mod.embed(["x"], settings, model=FakeModel(dim=3))
    large = embed_mod.embed(["x"], settings, model=FakeModel(dim=8))
    assert len(small[0]) == 3
    assert len(large[0]) == 8


@pytest.mark.skipif(
    os.getenv("RUN_EMBED_SMOKE") != "1",
    reason="要下模型，设 RUN_EMBED_SMOKE=1 才跑",
)
def test_real_model_dim_matches_config(settings):
    """真模型跑一次，确认它吐出来的维度等于配置里的 EMBED_DIM。

    对不上就是灾难：向量表按配置的维度建，实际写进去的却是另一个维度。
    """
    out = embed_mod.embed(["测试"], settings)
    assert len(out[0]) == settings.embed_dim
