from app.config.db import close_connection,get_connection

def create_candidate(
        compiled_topic_id,topic_node_id,title,slug,article_md,diagram=None
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
            INSERT INTO candidate_articles (
                   compiled_topic_id,
                   topic_node_id,
                   title,
                   slug,
                   article_md,
                   diagram
                   )
                   VALUES (%s,%s,%s,%s,%s,%s)
                   RETURNING id;
                   """,(
                       compiled_topic_id
                       ,topic_node_id
                       ,title
                       ,slug
                       ,article_md
                       ,diagram
                   ))
    
    candidate_id = cursor.fetchone()[0]
    conn.commit()
    close_connection(conn)
    return candidate_id

def get_candidate(candidate_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
            SELECT * FROM candidate_articles WHERE id=%s;
                   """,(candidate_id))
    row = cursor.fetchone()
    close_connection(conn)
    return row


def list_candidate(status="pending"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM candidate_articles WHERE status=%s ORDER BY created_at DESC;
                   """,(status,))
    rows = cursor.fetchall()
    close_connection(conn)
    return rows

def update_candidate_status(candidate_id,status,reason=None,rejected_by=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
            UPDATE candidate_articles SET status=%s, 
                   rejection_reason=%s, 
                   rejected_by=%s,
                   reviewed_at=NOW()
                   WHERE id=%s
                   """,(status,reason,rejected_by,id))
    conn.commit()
    close_connection(conn)
    