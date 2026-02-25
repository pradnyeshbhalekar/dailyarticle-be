from flask import Blueprint, jsonify
from app.models.published_articles import get_published_by_slug
from app.utils.auth_middleware import require_auth

public_article_routes = Blueprint(
    "public_articles",
    __name__
)

@public_article_routes.get("/<slug>")
def get_article(slug):
    user = require_auth()
    article = get_published_by_slug(slug)
    if not article:
        return jsonify({"error": "Not found"}), 404

    title, article_md, diagram, published_at = article

    return jsonify({
        "title": title,
        "content": article_md,
        "diagram": diagram,
        "published_at": published_at
    })