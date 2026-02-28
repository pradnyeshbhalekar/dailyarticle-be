from functools import wraps
from flask import abort,request
from app.utils.auth_middleware import require_auth
import os

def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = require_auth()
        if user["role"] != "admin":
            abort(403)
        return fn(user, *args, **kwargs)
    return wrapper


def require_editor(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = require_auth()
        if user["role"] not in ("admin", "editor"):
            abort(403)
        return fn(user, *args, **kwargs)
    return wrapper

def require_pipeline_secret():
    secret = request.headers.get("Authorization")
    if secret!=f"Bearer {os.getenv('PIPELINE_SECRET')}"