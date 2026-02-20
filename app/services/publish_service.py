from app.config.db import get_connection,close_connection
from app.models.published_articles import publish_article
from app.models.aritcle_candidate import update_candidate_status

def approve_candidate(candidate_id,admin_user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT topic_node_id, title, slug, article_md, diagram
        FROM candidate_articles
        WHERE id = %s AND status = 'pending';
    """, (candidate_id,))
    row = cursor.fetchone()
    if not row:
        close_connection(conn)
        raise ValueError( "Invalide candidate")
    
    topic_node_id,title,slug,article_md,diagram = row

    publish_article(
        candidate_id,
        topic_node_id,
        title,slug,article_md,diagram,admin_user_id
    )

    update_candidate_status(
        candidate_id=candidate_id,
        status="approved",
        reviewed_by=admin_user_id
    )

    close_connection(conn)

def reject_candidate(candidate_id,reason,admin_user_id):
    update_candidate_status(
        candidate_id=candidate_id,
        status="rejected",
        reason=reason,
        reviewed_by=admin_user_id
    )