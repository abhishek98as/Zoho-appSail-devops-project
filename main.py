from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)


@app.route("/health", methods=["GET"])  # Simple health check
def health():
    return "ok", 200


@app.route("/webhook", methods=["GET"])  # Verification for providers that send a challenge
def verify_webhook():
    # Common param names used by providers (e.g., hub.challenge for Meta, "challenge" for others)
    challenge = (
        request.args.get("hub.challenge")
        or request.args.get("challenge")
        or request.args.get("challange")  # keep backward-compat with existing spelling
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

    # Append payloads to a local log file for inspection
    try:
        with open("webhook.txt", "a", encoding="utf-8") as f:
            f.write(json.dumps(msgdata, ensure_ascii=False) + "\n")
    except Exception as e:
        # If file writes fail (e.g., on read-only FS), still return 200
        app.logger.warning(f"Failed to write webhook.txt: {e}")

    # Echo a minimal acknowledgement
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    # Local dev server. In AppSail, Procfile with gunicorn will be used.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

