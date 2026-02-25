from app.config.db import get_connection,close_connection

def get_auth_context(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT role FROM user_roles WHERE user_id = %s",
        (user_id,)   # ← COMMA
    )
    role_row = cursor.fetchone()
    role = role_row[0] if role_row else "viewer"

    cursor.execute(
        "SELECT plan_id, status FROM subscriptions WHERE user_id = %s",
        (user_id,)   # ← COMMA AGAIN
    )
    sub_row = cursor.fetchone()

    subscription = {
        "plan": sub_row[0],
        "status": sub_row[1]
    } if sub_row else None

    close_connection(conn)

    return {
        "role": role,
        "subscription": subscription
    }