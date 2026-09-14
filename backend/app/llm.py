import httpx
from app.config import Settings

TIMEOUT=60.0

def chat(messages:list[dict],settings:Settings,*,json_mode:bool = False,client:httpx.Client | None=None)->str:
    client=client or httpx.Client(timeout=TIMEOUT)
    payload={
        "model":settings.deepseek_model,
        "messages":messages,
    }
    if json_mode:
        payload["response_format"]={"type":"json_object"}
    resp=client.post(
        f"{settings.deepseek_base_url}/chat/completions",
        headers={"Authorization":f"Bearer {settings.deepseek_api_key}"},
        json=payload,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]