from flask import Flask, request, jsonify
from upstash_redis import Redis
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
redis_client = Redis(url=os.getenv("REDIS_URL", ""), token=os.getenv("REDIS_TOKEN", ""))

HIGH_SCORE_KEY = "tetris_highscore"

@app.route('/highscore', methods=['GET'])
def get_highscore():
    score = redis_client.get(HIGH_SCORE_KEY)
    if score is None:
        score = 0
    else:
        score = int(score)
    return jsonify({"highscore": score})

@app.route('/highscore', methods=['POST'])
def update_highscore():
    data = request.get_json()
    new_score = data.get("score", 0)
    current_score = redis_client.get(HIGH_SCORE_KEY)
    if current_score is None:
        current_score = 0
    else:
        current_score = int(current_score)

    if isinstance(new_score, int) and new_score > current_score:
        redis_client.set(HIGH_SCORE_KEY, new_score)
        current_score = new_score
    return jsonify({"highscore": current_score})
