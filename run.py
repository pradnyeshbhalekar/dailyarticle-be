from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "Flask is running ✅"

@app.route("/api/test")
def test():
    return jsonify({"message": "API working ✅"})

if __name__ == "__main__":
    app.run(debug=True)
