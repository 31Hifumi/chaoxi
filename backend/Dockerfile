FROM python:3.12-slim

# uv 从腾讯源装。不用 ghcr.io——实测那个 23MB 的层在国内下了 23 分钟还没完
RUN pip install --no-cache-dir -i https://mirrors.cloud.tencent.com/pypi/simple/ uv

WORKDIR /app

# 依赖单独一层：源码改了不会让这层缓存失效
COPY pyproject.toml uv.lock ./
# 源写在命令行上，不用 UV_DEFAULT_INDEX——那个变量实测没生效，uv 还是往国外拉
RUN uv sync --frozen --no-dev --default-index https://mirrors.cloud.tencent.com/pypi/simple/

COPY app ./app

ENV CHAOXI_DB=/data/chaoxi.db
EXPOSE 8000
# 直调 venv 里的 uvicorn。不走 `uv run`——那会让容器每次启动都联网同步一遍环境
# （还会把 dev 依赖也装上），网一拖就起不来
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
