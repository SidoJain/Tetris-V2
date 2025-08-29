from flask import Flask, request, jsonify
import redis
import os

app = Flask(__name__)
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:5000"))

HIGH_SCORE_KEY = "tetris_highscore"

@app.route('/highscore', methods=['GET'])
async def get_highscore():
    score = await redis_client.get(HIGH_SCORE_KEY)
    if score is None:
        score = 0
    else:
        score = int(score)
    return jsonify({"highscore": score})

@app.route('/highscore', methods=['POST'])
async def update_highscore():
    data = await request.get_json()
    new_score = data.get("score", 0)
    current_score = await redis_client.get(HIGH_SCORE_KEY)
    if current_score is None:
        current_score = 0
    else:
        current_score = int(current_score)
    if isinstance(new_score, int) and new_score > current_score:
        await redis_client.set(HIGH_SCORE_KEY, new_score)
        current_score = new_score
    return jsonify({"highscore": current_score})
