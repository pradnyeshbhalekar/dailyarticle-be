from flask import Blueprint, jsonify, request
from app.models.article_candidate import list_candidates
from app.services.publish_service import approve_candidate, reject_candidate
from app.utils.auth_decorators import require_admin

admin_candidate_routes = Blueprint("admin_candidates", __name__)

@admin_candidate_routes.get("/")
@require_admin
def pending_candidates(user):
    rows = list_candidates("pending")
    return jsonify(rows)


@admin_candidate_routes.post("/approve/<candidate_id>")
@require_admin
def approve(user, candidate_id):
    published_date = request.json.get("publish_date")
    approve_candidate(candidate_id, user["user_id"],published_date)
    return {"status": "approved"}


@admin_candidate_routes.post("/reject/<candidate_id>")
@require_admin
def reject(user, candidate_id):
    reason = request.json.get("reason")
    reject_candidate(candidate_id, reason, user["user_id"])
    return {"status": "rejected"}