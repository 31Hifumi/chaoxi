import sqlite_vec

def upsert_profile(conn,key,value,*,evidence=None,confidence=0.5):
    with conn:
        conn.execute("""INSERT INTO profile (key,value,evidence,confidence) VALUES(?,?,?,?)
                        ON CONFLICT(key) DO UPDATE 
                        SET value=excluded.value,
                            evidence=excluded.evidence,
                            confidence=excluded.confidence,
                            updated_at=datetime('now')""",(key,value,evidence,confidence),)

def list_profile(conn)->list[dict]:
    rows=conn.execute("""
    SELECT key,value,evidence,confidence,updated_at
    FROM profile
    ORDER BY confidence DESC,updated_at DESC
    """).fetchall()
    return [dict(r) for r in rows]

def delete_profile(conn,key)->None:
    with conn:
        conn.execute("DELETE FROM profile WHERE key =?",(key,))

def add_event(conn,content,*,kind,importance=5,embedding=None):
    with conn:
        cur=conn.execute("INSERT INTO events (content,kind,importance) VALUES(?,?,?)",(content,kind,importance))
        event_id = cur.lastrowid
        if embedding is not None:
            conn.execute(
                "INSERT INTO vec_events (event_id, valid, embedding) VALUES (?, ?, ?)",
                (event_id, 1, sqlite_vec.serialize_float32(embedding)),
            )
        return event_id

def recent_events(conn,n:int | None=None)->list[dict]:
    if n or n==0:
        rows=conn.execute("""
        SELECT id,content,kind,importance,created_at
        FROM events
        ORDER BY created_at DESC,id DESC LIMIT ?
        """,(n,)).fetchall()
    else:
        rows = conn.execute("""
                SELECT id,content,kind,importance,created_at
                FROM events
                ORDER BY created_at DESC,id DESC
                """).fetchall()
    return [dict(r) for r in rows]

def add_chunks(conn,doc_id:str,chunks:list[str],embeddings=None):
    if embeddings is not None and len(chunks) != len(embeddings):
        raise ValueError("chunks 与 embeddings 数量不一致")
    with conn:
        # 1. 先找出旧 chunk_id，删掉对应向量
        old_ids = [r[0] for r in conn.execute(
            "SELECT id FROM chunks WHERE doc_id = ?", (doc_id,)
        )]
        if old_ids:
            conn.executemany(
                "DELETE FROM vec_chunks WHERE chunk_id = ?",
                [(i,) for i in old_ids],
            )
        # 2. 删 chunks
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        # 3. 重插
        for i, c in enumerate(chunks):
            cur = conn.execute(
                "INSERT INTO chunks (doc_id, ordinal, content) VALUES (?, ?, ?)",
                (doc_id, i, c),
            )
            if embeddings is not None:
                conn.execute(
                    "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
                    (cur.lastrowid, sqlite_vec.serialize_float32(embeddings[i])),
                )

def init_vec_tables(conn,dim:int)->None:
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_events "
        f"USING vec0(event_id INTEGER PRIMARY KEY,valid INTEGER,embedding float[{dim}])"
    )
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks "
        f"USING vec0(chunk_id INTEGER PRIMARY KEY,embedding float[{dim}])"
    )

def search_chunks(conn,query_vec,k:int)->list[dict]:
    serialized = sqlite_vec.serialize_float32(query_vec)
    rows=conn.execute("""
    SELECT c.id,c.doc_id,c.ordinal,c.content,v.distance
    FROM(
        SELECT chunk_id, distance
        FROM vec_chunks
        WHERE embedding MATCH ?
        AND k = ?
    )v
    JOIN chunks c ON c.id=v.chunk_id
    ORDER BY v.distance
    """,(serialized,k)).fetchall()
    return [dict(r) for r in rows]

def search_events(conn,query_vec,k:int)->list[dict]:
    serialized = sqlite_vec.serialize_float32(query_vec)
    rows=conn.execute("""
    SELECT e.id,e.content,e.kind,e.importance,e.created_at,v.distance
    FROM(
        SELECT event_id, distance
        FROM vec_events
        WHERE embedding MATCH ?
        AND k = ?
        AND valid=1
    )v
    JOIN events e ON e.id=v.event_id
    ORDER BY v.distance
    """,(serialized,k)).fetchall()
    return [dict(r) for r in rows]