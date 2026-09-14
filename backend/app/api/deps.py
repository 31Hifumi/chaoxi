from app.db import connect
from fastapi import Request
from app.llm import chat

def get_conn(request:Request):
    conn=connect(request.app.state.settings.db_path)
    try:yield conn
    finally: conn.close()

def get_llm(request:Request):
    client=request.app.state.http_client
    settings=request.app.state.settings
    def call(messages,**kw):
        return chat(messages,settings,client=client,**kw)
    return call