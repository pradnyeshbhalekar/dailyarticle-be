from flask import request,abort
from app.utils.jwt_utils import decode_jwt

def require_auth():
    header = request.headers.get("Authorization")
    if not header or not header.startswith("Bearer "):
        abort(401)

    token = header.split(" ")[1]

    try:
        return decode_jwt(token)
    except Exception:
        abort(401)