from app.db.session import create_session,get_session,add_message,get_messages
COUNT=20 #历史消息条数

class SessionNotFound(Exception):
    pass

def chat_once(conn,llm,session_id:int | None,message:str)->tuple[int,str]:
    if session_id is None:
        session_id = create_session(conn,message[:20])
    else:
        if get_session(conn,session_id) is None:
            raise SessionNotFound
    add_message(conn,session_id,role="user",content=message)
    messages=get_messages(conn,session_id,COUNT)
    reply = llm(messages)
    add_message(conn, session_id, role="assistant", content=reply)
    return session_id,reply