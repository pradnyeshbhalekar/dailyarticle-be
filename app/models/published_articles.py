from app.config.db import close_connection,get_connection

def create_published_articles():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS published_articles(
                   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                   candidate_id UUID NOT NULL
                        REFERENCES article_candidates(id),
                   topic_node_id UUID NOT NULL
                        REFERENCES concept_nodes(id),
                   title TEXT NOT NULL,
                   slug TEXT NOT NULL,
                   article_md TEXT NOT NULL,
                   diagram TEXT NOT NULL,
                   published_at TIMESTAMP DEFAULT NOW(),
                   published_by UUID
                   )
                   """)
    conn.commit()
    close_connection(conn)
    print("published_articles created")