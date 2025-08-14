from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

@app.route("/")
def index():
    return "ok", 200


@app.route("/health", methods=["GET"])  # Simple health check
def health():
    return "ok", 200


@app.route("/webhook", methods=["GET"])  # Verification for providers that send a challenge
def verify_webhook():
    challenge = (
        request.args.get("hub.challenge")
        or request.args.get("challenge")
        or request.args.get("challange")
    )
    if challenge:
        return challenge, 200
    return "ok", 200


@app.route("/webhook", methods=["POST"])  # Receive webhook events
def webhook():
    try:
        msgdata = request.get_json(force=True, silent=True) or {}
    except Exception:
        msgdata = {}

    try:
        with open("webhook.txt", "a", encoding="utf-8") as f:
            f.write(json.dumps(msgdata, ensure_ascii=False) + "\n")
    except Exception as e:
        app.logger.warning(f"Failed to write webhook.txt: {e}")

    return jsonify(status="ok"), 200

if __name__ == "__main__":
    port = int(os.environ.get("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))
    app.run(host="0.0.0.0", port=port)
