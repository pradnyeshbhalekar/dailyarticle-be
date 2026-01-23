from app.config.db import get_connection, close_connection

ANTI_REPEAT_DAYS = 30
MAX_TRIES = 10


def pick_topic():
    conn = get_connection()
    cursor = conn.cursor()

    picked_id = None
    picked_name = None

    for _ in range(MAX_TRIES):

        # 1) pick random domain
        cursor.execute("""
            SELECT id, name
            FROM concept_nodes
            WHERE node_type = 'domain'
            ORDER BY RANDOM()
            LIMIT 1;
        """)
        domain = cursor.fetchone()

        if not domain:
            close_connection(conn)
            return None

        domain_id, domain_name = domain

        # 2) pick a connected concept (if exists)
        cursor.execute("""
            SELECT cn.id, cn.name
            FROM concept_edges ce
            JOIN concept_nodes cn ON cn.id = ce.to_node_id
            WHERE ce.from_node_id = %s
            ORDER BY (RANDOM() * ce.strength) DESC
            LIMIT 1;
        """, (domain_id,))
        candidate = cursor.fetchone()

        # if no edges yet, fallback to domain itself
        picked_id, picked_name = candidate if candidate else (domain_id, domain_name)

        # 3) anti-repeat check (last 30 days)
        cursor.execute(f"""
            SELECT 1
            FROM topic_history
            WHERE topic_node_id = %s
              AND used_at >= NOW() - INTERVAL '{ANTI_REPEAT_DAYS} days'
            LIMIT 1;
        """, (picked_id,))
        repeated = cursor.fetchone()

        # ✅ if not repeated, accept topic
        if not repeated:
            break

    # 4) save usage (history + last_used_at)
    cursor.execute("""
        UPDATE concept_nodes
        SET last_used_at = NOW()
        WHERE id = %s;
    """, (picked_id,))

    cursor.execute("""
        INSERT INTO topic_history (topic_node_id)
        VALUES (%s);
    """, (picked_id,))

    conn.commit()
    close_connection(conn)

    return {"topic_node_id": str(picked_id), "topic_name": picked_name}