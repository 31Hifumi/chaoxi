import httpx
from app.api import chat
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import init_db,connect
from app.config import  load_settings

@asynccontextmanager
async def lifespan(app:FastAPI):
    with httpx.Client(timeout=60) as client:
        app.state.http_client = client
        app.state.settings=load_settings()
        conn = connect(app.state.settings.db_path)
        init_db(conn)
        yield


def create_app()->FastAPI:
    app=FastAPI(lifespan=lifespan)
    app.include_router(chat.router,prefix="/api")
    return app


app = create_app()