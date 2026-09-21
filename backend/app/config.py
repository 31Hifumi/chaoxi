import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    db_path: Path
    embed_model: str = "BAAI/bge-small-zh-v1.5"
    embed_dim: int = 512  # 必须和 embed_model 对得上，否则向量表会建错
    embed_path: str = "D:/fastembed-cache"  # 模型缓存放哪（默认也是 FASTEMBED_CACHE_PATH）

def load_settings() -> Settings:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("缺少环境变量 DEEPSEEK_API_KEY")
    return Settings(
        deepseek_api_key=api_key,
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
        db_path=Path(os.getenv("CHAOXI_DB", "chaoxi.db")),
        embed_model=os.getenv("EMBED_MODEL", "BAAI/bge-small-zh-v1.5"),
        embed_dim=int(os.getenv("EMBED_DIM", "512")),
        embed_path=os.getenv("FASTEMBED_CACHE_PATH", "D:/fastembed-cache"),
    )