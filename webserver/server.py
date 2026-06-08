#!/usr/bin/env python3
"""
server.py — Iframe viewer + n8n chat window.

Usage:
    pip install -r requirements.txt
    python server.py
    python server.py --host 0.0.0.0 --port 8080

Settings are persisted to config.json (gitignored).
Visit /settings to configure the iframe URL and webhook.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
except ImportError:
    sys.exit("Missing dependency: run  pip install -r requirements.txt")

try:
    import requests as http
except ImportError:
    sys.exit("Missing dependency: run  pip install -r requirements.txt")


CONFIG_FILE = Path(__file__).parent / "config.json"

DEFAULT_CONFIG: dict = {
    "iframe_url": "",
    "webhook_url": "",
    "auth_header": "",
    "auth_token": "",
    "chat_title": "Chat",
}

app = Flask(__name__)
app.secret_key = "change-me-to-something-random-in-production"


# ── Config helpers ─────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_CONFIG, **saved}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", config=load_config())


@app.route("/settings", methods=["GET", "POST"])
def settings():
    cfg = load_config()
    if request.method == "POST":
        cfg["iframe_url"]  = request.form.get("iframe_url",  "").strip()
        cfg["webhook_url"] = request.form.get("webhook_url", "").strip()
        cfg["auth_header"] = request.form.get("auth_header", "").strip()
        cfg["auth_token"]  = request.form.get("auth_token",  "").strip()
        cfg["chat_title"]  = request.form.get("chat_title",  "Chat").strip()
        save_config(cfg)
        flash("Settings saved.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", config=cfg)


@app.route("/chat", methods=["POST"])
def chat():
    """Proxy chat messages to the n8n webhook to avoid CORS issues."""
    cfg = load_config()
    webhook_url = cfg.get("webhook_url", "").strip()

    if not webhook_url:
        return jsonify({"error": "No webhook URL set. Go to /settings to add one."}), 400

    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Empty message."}), 400

    headers = {"Content-Type": "application/json"}
    auth_header = cfg.get("auth_header", "").strip()
    auth_token  = cfg.get("auth_token",  "").strip()
    if auth_header and auth_token:
        headers[auth_header] = auth_token

    try:
        resp = http.post(
            webhook_url,
            json={"message": message},
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
    except http.exceptions.ConnectionError:
        return jsonify({"error": "Could not reach the webhook URL. Is n8n running?"}), 502
    except http.exceptions.Timeout:
        return jsonify({"error": "Webhook timed out after 60 seconds."}), 504
    except http.exceptions.HTTPError:
        return jsonify({"error": f"Webhook returned HTTP {resp.status_code}."}), 502

    # Parse the response — n8n can return various shapes
    reply = _extract_reply(resp)
    return jsonify({"reply": reply})


def _extract_reply(resp: "http.Response") -> str:
    """Pull the human-readable reply out of whatever n8n sends back."""
    try:
        data = resp.json()
    except ValueError:
        return resp.text.strip() or "(empty response)"

    # Unwrap array: n8n often returns [{...}]
    if isinstance(data, list):
        data = data[0] if data else {}

    if isinstance(data, dict):
        for key in ("response", "text", "output", "message", "reply", "content", "result"):
            if data.get(key):
                val = data[key]
                return val if isinstance(val, str) else json.dumps(val)
        # Nothing matched — return the whole object as JSON
        return json.dumps(data, indent=2)

    return str(data)


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Iframe viewer + n8n chat window.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    args = parser.parse_args()

    cfg = load_config()
    if not cfg["iframe_url"] and not cfg["webhook_url"]:
        print(f"  Tip: visit http://{args.host}:{args.port}/settings to configure the app.")

    print(f"  Serving at  http://{args.host}:{args.port}")
    print(f"  Settings    http://{args.host}:{args.port}/settings")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
