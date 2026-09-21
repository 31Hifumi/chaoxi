import sqlite3
from pathlib import Path
import sqlite_vec

SCHEMA=Path(__file__).parent / "schema.sql"
def connect(db_path) ->sqlite3.Connection:
    conn=sqlite3.connect(str(db_path))
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn

def init_db(conn:sqlite3.Connection) ->None:
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()

