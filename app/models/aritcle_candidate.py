from config.db import get_connection,close_connection

def create_article_candidate():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS article_candidate(
                   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                   compiled_topic_id UUID NOT NULL
                        REFERENCES compiled_topics(id) ON DELETE CASCADE
                   topic_node_id UUID NOT NULL
                        REFERENCES concept_nodes(id) ON DELETE CASCADE,
                   title TEXT NOT NULL,
                   slug TEXT NOT NULL,
                   article_md TEXT NOT NULL,
                   diagram TEXT,
                    status TEXT NOT NULL CHECK (
        status IN ('pending', 'approved', 'rejected')
    ) DEFAULT 'pending',
                    rejection_reason TEXT,
                   rejected_by TEXT,
                    reviewed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                   )
                   """)
    conn.commit()
    close_connection(conn)
    print("article_candidate created successfully")