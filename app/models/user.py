from app.config.db import get_connection,close_connection

def create_user_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
                   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                   email TEXT UNIQUE NOT NULL,
                   is_active BOOLEAN DEFAULT TRUE,
                   created_at TIMESTAMP DEFAULT NOW());
                   """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
                   user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                  role TEXT NOT NULL CHECK (
                    role IN ('admin', 'editor', 'viewer')
                    ),
                PRIMARY KEY (user_id)
                   """)
    

    conn.commit()
    close_connection(conn)
    print("created users and user_roles tables successfully")

def create_plans_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                   name TEXT,
                   monthly_price INTEGER,
                   features JSONB);
                   """)
    
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                   user_id UUID REFERENCES users(id),
                   plan_id TEXT REFERENCES plans(id),
                   status TEXT CHECK (
                    status IN ('active', 'paused', 'cancelled')
                    ),
                started_at TIMESTAMP,
                ends_at TIMESTAMP,
                PRIMARY KEY (user_id)
                   )
                   """)
    
    conn.commit()
    close_connection(conn)
    print('created plans and subscriptions successfully')