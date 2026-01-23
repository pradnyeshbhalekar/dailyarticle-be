from flask import Flask, jsonify
from flask_cors import CORS

from app.models.schema import init_db
from app.models.graph import insert_node, get_all_nodes, insert_or_increment_edge
from app.routes.topic import topic_bp

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return "Flask is running ✅"


@app.route("/api/test")
def test():
    return jsonify({"message": "API working ✅"})


@app.route("/api/init-db", methods=["POST"])
def init_database():
    init_db()
    return jsonify({"message": "✅ Database initialized"})


app.register_blueprint(topic_bp, url_prefix="/api")





if __name__ == "__main__":
    app.run(debug=True)
