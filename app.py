import os
import re
import threading
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request

from consumer import consume_news_for_company
from producer import get_company_news, produce_news
from start_kafka import start_kafka

app = Flask(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
SYSTEM_PROMPT = (
    "You are the MarketEcho assistant. Help users understand the sentiment dashboard, "
    "explain headlines, and answer questions about the app. Keep answers concise."
)

NEWS_KEYWORDS = ("news", "headline", "headlines", "updates", "stock", "price", "shares")
FILLER_WORDS = {
    "give",
    "me",
    "the",
    "a",
    "an",
    "new",
    "newer",
    "latest",
    "recent",
    "today",
    "please",
    "headlines",
    "headline",
    "news",
    "updates",
    "stock",
    "price",
    "shares",
    "about",
    "for",
    "on",
    "of",
}

pipeline_lock = threading.Lock()
kafka_lock = threading.Lock()

kafka_started = False
producer_thread = None
consumer_thread = None
stop_event = None

state = {
    "running": False,
    "company": None,
    "updated_at": None,
    "error": None,
    "summary": {
        "counts": {"positive": 0, "negative": 0, "neutral": 0},
        "most_positive": {"headline": "", "score": 0},
        "most_negative": {"headline": "", "score": 0},
        "overall": "neutral",
        "confidence": 0.0,
        "headlines": [],
    },
}


def ollama_chat(messages):
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", ""), None
    except requests.RequestException as exc:
        return "", (
            "Ollama is unavailable. Make sure it is running and the model is pulled. "
            f"Details: {exc}"
        )


def fallback_chat_reply(prompt, error_message=None):
    lower = prompt.lower()

    if any(word in lower for word in ("start", "run", "pipeline", "analysis")):
        base = (
            "To run analysis: enter a company name, click Start, then watch live sentiment metrics "
            "update every few seconds. Click Stop to end the stream."
        )
    elif any(word in lower for word in ("sentiment", "confidence", "positive", "negative", "neutral")):
        base = (
            "MarketEcho classifies headlines as positive, negative, or neutral and computes an overall "
            "sentiment with confidence from the rolling stream."
        )
    elif any(word in lower for word in ("kafka", "topic", "producer", "consumer")):
        base = (
            "Kafka streams headlines on the financial-news topic: producer fetches news, consumer scores "
            "sentiment, and the dashboard polls /api/status for updates."
        )
    else:
        base = (
            "I can help with pipeline controls, sentiment metrics, and headline summaries. "
            "Ask about a company (for example: latest news for Tesla)."
        )

    if error_message:
        return f"{base}\n\nNote: {error_message}"
    return base


def normalize_company(candidate):
    cleaned = candidate.strip(" .,:;!?")
    tokens = [token for token in re.split(r"\s+", cleaned) if token]
    remaining = [token for token in tokens if token.lower() not in FILLER_WORDS]
    if not remaining:
        return None
    return " ".join(remaining)


def extract_company_from_prompt(prompt):
    lower = prompt.lower()
    if not any(keyword in lower for keyword in NEWS_KEYWORDS):
        return None

    patterns = [
        r"(?:news|headlines|updates)\s+(?:on|about|for)\s+([A-Za-z][A-Za-z0-9 .&-]{1,40})",
        r"(?:stock|shares|price)\s+of\s+([A-Za-z][A-Za-z0-9 .&-]{1,40})",
        r"([A-Za-z][A-Za-z0-9 .&-]{1,40})\s+(?:stock|shares|price|news|headlines|updates)",
    ]

    for pattern in patterns:
        match = re.search(pattern, prompt, flags=re.IGNORECASE)
        if match:
            normalized = normalize_company(match.group(1))
            if normalized:
                return normalized

    return None


def summarize_headlines(company, headlines):
    if not headlines:
        return ""

    trimmed = headlines[:10]
    prompt_lines = "\n".join(f"- {headline}" for headline in trimmed)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Summarize these {company} headlines in 3-5 sentences for a casual "
                f"investor. Do not list the headlines.\n{prompt_lines}"
            ),
        },
    ]
    summary, _ = ollama_chat(messages)
    if summary.strip():
        return summary.strip()

    sample = ", ".join(headlines[:3])
    return (
        f"Recent coverage for {company} is mixed across major outlets. "
        f"Top themes include: {sample}. "
        "Review the latest headlines below for source-level details."
    )


def ensure_kafka_started():
    global kafka_started

    with kafka_lock:
        if kafka_started:
            return True

        kafka_started = start_kafka()
        return kafka_started


def reset_state(company):
    state["running"] = True
    state["company"] = company
    state["updated_at"] = datetime.utcnow().isoformat()
    state["error"] = None
    state["summary"] = {
        "counts": {"positive": 0, "negative": 0, "neutral": 0},
        "most_positive": {"headline": "", "score": 0},
        "most_negative": {"headline": "", "score": 0},
        "overall": "neutral",
        "confidence": 0.0,
        "headlines": [],
    }


def stop_pipeline_locked():
    global producer_thread, consumer_thread, stop_event

    if stop_event is not None:
        stop_event.set()

    state["running"] = False

    producer_thread = None
    consumer_thread = None
    stop_event = None


def consumer_worker(company, local_stop_event):
    try:
        for counts, most_pos, most_neg, overall, conf, all_headlines in consume_news_for_company(
            company, stop_event=local_stop_event
        ):
            with pipeline_lock:
                if local_stop_event.is_set() or state["company"] != company:
                    break

                state["summary"] = {
                    "counts": counts,
                    "most_positive": most_pos,
                    "most_negative": most_neg,
                    "overall": overall,
                    "confidence": round(conf, 2),
                    "headlines": all_headlines,
                }
                state["updated_at"] = datetime.utcnow().isoformat()
    except Exception as exc:
        with pipeline_lock:
            state["error"] = str(exc)
            state["running"] = False


@app.route("/")
def index():
    return render_template("index.html", model_name=OLLAMA_MODEL)


@app.post("/api/start")
def api_start():
    payload = request.get_json(silent=True) or {}
    company = (payload.get("company") or "").strip()

    if not company:
        return jsonify({"ok": False, "error": "Company name is required."}), 400

    if not ensure_kafka_started():
        return jsonify({"ok": False, "error": "Failed to start Kafka."}), 500

    global producer_thread, consumer_thread, stop_event

    with pipeline_lock:
        stop_pipeline_locked()
        reset_state(company)

        stop_event = threading.Event()
        local_stop_event = stop_event

        producer_thread = threading.Thread(
            target=produce_news,
            args=(company, local_stop_event),
            daemon=True,
        )
        consumer_thread = threading.Thread(
            target=consumer_worker,
            args=(company, local_stop_event),
            daemon=True,
        )

        producer_thread.start()
        consumer_thread.start()

    return jsonify({"ok": True, "message": f"Pipeline started for {company}."})


@app.post("/api/stop")
def api_stop():
    with pipeline_lock:
        stop_pipeline_locked()

    return jsonify({"ok": True, "message": "Pipeline stopped."})


@app.get("/api/status")
def api_status():
    with pipeline_lock:
        counts = state["summary"]["counts"]
        total_news = sum(counts.values())

        return jsonify(
            {
                "ok": True,
                "running": state["running"],
                "company": state["company"],
                "updated_at": state["updated_at"],
                "error": state["error"],
                "summary": {
                    **state["summary"],
                    "total_news": total_news,
                },
            }
        )


@app.post("/api/chat")
def api_chat():
    payload = request.get_json(silent=True) or {}
    prompt = (payload.get("prompt") or "").strip()

    if not prompt:
        return jsonify({"ok": False, "error": "Prompt is required."}), 400

    company_from_chat = extract_company_from_prompt(prompt)
    if company_from_chat:
        headlines = get_company_news(company_from_chat)
        if headlines:
            summary = summarize_headlines(company_from_chat, headlines).strip()
            if not summary:
                summary = "Here is a quick summary of the latest coverage."
            latest_headlines = "\n".join(f"- {headline}" for headline in headlines[:10])
            reply = (
                f"{summary}\n\nLatest headlines for {company_from_chat}:\n"
                f"{latest_headlines}"
            )
        else:
            reply = f"I couldn't find recent headlines for {company_from_chat}."
    else:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        reply, error = ollama_chat(messages)
        if not reply.strip():
            reply = fallback_chat_reply(prompt, error)

    return jsonify({"ok": True, "reply": reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
