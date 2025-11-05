import psycopg2
import psycopg2.extras
from flask import current_app

def conectar():
    cfg = current_app.config
    return psycopg2.connect(
        host=cfg["DB_HOST"],
        user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"],
        database=cfg["DB_NAME"],
        port=cfg["DB_PORT"]
    )
    
def q_all(sql, params=(), dictcur=True):
    con = conectar()
    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor if dictcur else None)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    con.close()
    
    if dictcur and rows:
        return [dict(row) for row in rows]
    return rows

def q_one(sql, params=(), dictcur=True):
    rows = q_all(sql, params, dictcur=dictcur)
    return rows[0] if rows else None

def q_exec(sql, params=()):
    con = conectar()
    cur = con.cursor()
    cur.execute(sql, params)
    con.commit()
    
    # Para PostgreSQL, obtener el último ID insertado
    if sql.strip().upper().startswith('INSERT'):
        cur.execute("SELECT LASTVAL()")
        last_id = cur.fetchone()[0]
    else:
        last_id = None
        
    cur.close()
    con.close()
    return last_id