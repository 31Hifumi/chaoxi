# 潮汐 chaoxi

个人 AI 助理。目前跑通的是后端 walking skeleton：一条 `POST /api/chat` 走完「建/取会话 → 落库 → 调模型 → 存回复」。

## 技术栈

Python 3.12 · FastAPI · SQLite(WAL) · httpx 直连 DeepSeek · uv · pytest

## 目录

```
backend/
├── app/
│   ├── config.py         环境变量 → Settings
│   ├── llm.py            单次对话（DeepSeek chat completions）
│   ├── db/               连接与建表；session.py 管会话和消息的读写
│   ├── services/chat.py  一轮聊天的编排：落库 + 调模型
│   ├── api/              deps.py 提供依赖，chat.py 是路由
│   └── main.py           组装 app
└── tests/                30 个用例，全程不联网
```

分层是单向的：`api → services → db`。service 不认识 HTTP，路由不写 SQL。

## 跑起来

```bash
cd backend
uv sync
cp .env.example .env        # 填上 DEEPSEEK_API_KEY
uv run uvicorn app.main:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id": null, "message": "你好"}'
```

`session_id` 传 `null` 开新会话，传已有 id 续聊；id 不存在返回 404。

## 测试

```bash
cd backend
uv run pytest
```

LLM 通过依赖覆盖换成假的，所以测试不联网、不花钱。
