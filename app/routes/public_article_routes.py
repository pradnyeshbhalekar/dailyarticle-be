from flask import Blueprint, jsonify
from app.models.published_articles import get_published_by_slug,get_todays_published_article
from app.utils.auth_middleware import require_auth
from app.utils.auth_decorators import require_admin


public_article_routes = Blueprint(
    "public_articles",
    __name__
)

@public_article_routes.get("/<slug>")
def get_article(slug):
    # user = require_auth()
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


@public_article_routes.get("/today")
def today_article():
    user = require_auth()
    article = get_todays_published_article()
    if not article:
        return jsonify({"error":"No article published today"}),404
    
    return jsonify(article)