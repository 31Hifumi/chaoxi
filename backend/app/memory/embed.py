"""嵌入：文本 → 向量。

三条约束：
  1. 维度从 settings 来，不写死在代码里——换模型时只要保证 EMBED_DIM 跟着改
  2. 模型可注入：测试传假实现，不碰网络也不下模型
  3. 模型对象缓存在进程里，别每次调用都重载（重载要好几秒）

缓存目录不用代码管：fastembed 自己读环境变量 FASTEMBED_CACHE_PATH。
"""

from app.config import Settings

_model = None  # 进程级缓存


def _default_model(settings: Settings):
    """真实现：本地 fastembed。

    首次加载会去下模型。国内要同时设两个环境变量（见 .env.example）：
      HF_ENDPOINT=https://hf-mirror.com   —— 走镜像
      HF_HUB_DISABLE_XET=1                —— hf-mirror 不代理 Xet，不禁会 401
    """
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(
            model_name=settings.embed_model,
            cache_dir=settings.embed_path,
        )
    return _model


def embed(texts: list[str], settings: Settings, *, model=None) -> list[list[float]]:
    """把一批文本转成向量，返回顺序与输入一致。

    空输入直接返回，不去加载模型（加载要下 100MB）。
    fastembed 吐的是生成器 + numpy 数组，这里统一成 list[list[float]]。
    """
    if not texts:
        return []
    model = model or _default_model(settings)
    return [[float(x) for x in vec] for vec in model.embed(texts)]
