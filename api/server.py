from flask import Flask, jsonify, request
import os
import json
from threading import Lock

app = Flask(__name__)

STORE_FILE = os.path.join(os.path.dirname(__file__), "highscore.json")
_store_lock = Lock()

def read_highscore() -> int:
    with _store_lock:
        if not os.path.exists(STORE_FILE):
            return 0
        try:
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("highscore", 0))
        except Exception:
            return 0

def write_highscore(value: int) -> int:
    with _store_lock:
        try:
            with open(STORE_FILE, "w", encoding="utf-8") as f:
                json.dump({"highscore": int(value)}, f)
        except Exception:
            pass
        return int(value)

@app.get("/highscore")
def get_highscore():
    return jsonify({"highscore": read_highscore()})

@app.post("/highscore")
def post_highscore():
    try:
        payload = request.get_json(force=True) or {}
        score = int(payload.get("score", 0))
    except Exception:
        return jsonify({"error": "invalid payload"}), 400

    current = read_highscore()
    if score > current:
        current = write_highscore(score)
    return jsonify({"highscore": current})