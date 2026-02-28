from app.config.db import get_connection, close_connection

def create_user_table():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (
                    role IN ('admin', 'editor', 'viewer')
                ),
                PRIMARY KEY (user_id)
            );
        """)
        
        conn.commit()
        cursor.close()
        print("Created users and user_roles tables successfully")
    finally:
        close_connection(conn)

def create_plans_table():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT,
                monthly_price INTEGER,
                features JSONB
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id UUID REFERENCES users(id),
                plan_id UUID REFERENCES plans(id),
                status TEXT CHECK (
                    status IN ('active', 'paused', 'cancelled')
                ),
                started_at TIMESTAMP,
                ends_at TIMESTAMP,
                PRIMARY KEY (user_id)
            );
        """)
        
        conn.commit()
        cursor.close()
        print("Created plans and subscriptions successfully")
    finally:
        close_connection(conn)

def get_or_create_user(email: str):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM users WHERE email = %s
        """, (email,))
        
        row = cursor.fetchone()

        if row:
            return row[0]
        
        cursor.execute("""
            INSERT INTO users (email) VALUES (%s) RETURNING id
        """, (email,))
        user_id = cursor.fetchone()[0]

        conn.commit()
        return user_id
    finally:
        close_connection(conn)

def get_user_by_id(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
             SELECT
                u.id,
                u.email,
                u.is_active,
                r.role
            FROM users u
            LEFT JOIN user_roles r ON r.user_id = u.id
            WHERE u.id = %s
        """, (user_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "user_id": row[0],
            "email": row[1],
            "is_active": row[2],
            "role": row[3] or "viewer"
        }
    finally:
        close_connection(conn)