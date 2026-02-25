from flask import Blueprint, request, jsonify, abort
from google.oauth2 import id_token
from google.auth.transport import requests
import os
from app.models.user import get_or_create_user
from app.models.auth_context import get_auth_context
from app.utils.jwt_utils import create_jwt

auth_routes = Blueprint("auth_routes", __name__)

@auth_routes.post("/google")
def google_login():
    data = request.get_json(silent=True)
    if not data or "id_token" not in data:
        abort(400, "Missing id_token")

    try:
        payload = id_token.verify_oauth2_token(
            data["id_token"],
            requests.Request(),
            os.getenv("GOOGLE_CLIENT_ID")
        )
    except Exception:
        abort(401, "Invalid Google token")

    email = payload.get("email")
    if not email:
        abort(401)

    user_id = get_or_create_user(email)
    context = get_auth_context(user_id)

    jwt_token = create_jwt({
        "user_id": str(user_id),
        "email": email,
        "role": context["role"]
    })

    return jsonify({
        "access_token": jwt_token,
        "user": {
            "id": user_id,
            "email": email,
            "role": context["role"],
            "subscription": context["subscription"]
        }
    })