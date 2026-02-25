from flask import Blueprint, jsonify, request, abort
from app.models.article_candidate import list_candidates, get_candidate
from app.services.publish_service import approve_candidate, reject_candidate
from app.utils.auth_middleware import require_auth




admin_candidate_routes = Blueprint(
    "admin_candidates",
    __name__,
)

@admin_candidate_routes.route("/", methods=["GET"])
def pending_candidates():
    rows = list_candidates("pending")
    return jsonify(rows)



@admin_candidate_routes.post("/approve/<candidate_id>")
def approve(candidate_id):
    user = require_auth()
    if user["role"] != "admin":
        abort(403)

    approve_candidate(candidate_id, user["user_id"])
    return {"status": "approved"}


@admin_candidate_routes.post("/reject/<candidate_id>")
def reject(candidate_id):
    reason = request.json.get("reason")
    user = require_auth()
    if user["role"] != "admin":
        abort(403)
    reject_candidate(candidate_id, reason,user["user_id"])
    return jsonify({"status": "rejected"})