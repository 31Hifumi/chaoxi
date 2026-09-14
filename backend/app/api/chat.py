from app.api.deps import get_llm, get_conn
from app.services.chat import SessionNotFound, chat_once
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

router = APIRouter()

class ChatIn(BaseModel):
    session_id : int | None=None
    message : str

    @field_validator("message")
    @classmethod
    def check_message(cls,v:str):
        if not v.strip():
            raise ValueError("message不能为空")
        return v.strip()

class ChatOut(BaseModel):
    session_id :int
    reply : str

@router.post("/chat",response_model=ChatOut)
def create_chat(body:ChatIn,llm=Depends(get_llm),conn=Depends(get_conn)):
    try:
        session_id,reply=chat_once(conn,llm,body.session_id,body.message)
        return ChatOut(session_id=session_id, reply=reply)
    except SessionNotFound:
        raise HTTPException(status_code=404, detail="该会话不存在!")