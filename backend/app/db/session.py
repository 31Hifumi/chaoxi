
def create_session(conn,title:str) ->int:
    cur = conn.execute("INSERT INTO sessions(title) VALUES(?)",(title,),)
    conn.commit()
    return cur.lastrowid

def get_session(conn,session_id:int):
    row = conn.execute("SELECT id,title FROM sessions WHERE id = ?",(session_id,),).fetchone()
    return row

def add_message(conn,session_id:int,role:str,content:str)->int:
    cur = conn.execute("INSERT INTO messages(session_id,role,content) VALUES(?,?,?) ",(session_id,role,content),)
    conn.commit()
    return cur.lastrowid

def get_messages(conn,session_id:int,count:int | None=None)->list:
    rows= conn.execute("SELECT role,content FROM messages WHERE session_id = ? ORDER BY id DESC",(session_id,),).fetchall()
    rows = rows[:count][::-1]
    return [{"role":r["role"],"content":r["content"]} for r in rows]