import streamlit as st
import importlib.util
import threading
import os
import time
import re
from datetime import datetime
import requests

# --- Dynamically import and start Kafka ---
def load_and_start_kafka():
    kafka_path = os.path.join(os.path.dirname(__file__), "start_kafka.py")
    spec = importlib.util.spec_from_file_location("start_kafka", kafka_path)
    start_kafka = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(start_kafka)
    start_kafka.start_kafka()  # explicitly call it
    return True


# --- Streamlit setup ---
st.set_page_config(page_title="Financial News Sentiment Dashboard", layout="wide")
st.title("💹 Financial News Sentiment Dashboard")
st.caption("Real-time financial sentiment analysis using Kafka + AI")

# --- Chatbot configuration (Ollama) ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
SYSTEM_PROMPT = (
    "You are the MarketEcho assistant. Help users understand the sentiment dashboard, "
    "explain headlines, and answer questions about the app. Keep answers concise."
)


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
        return data.get("message", {}).get("content", "")
    except requests.RequestException as exc:
        return (
            "Chat error. Make sure Ollama is running and the model is pulled. "
            f"Details: {exc}"
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
    return ollama_chat(messages)




# --- Start Kafka once per session ---
if "kafka_started" not in st.session_state:
    st.info("🔍 Checking Kafka cluster status...")
    if load_and_start_kafka():
        st.session_state.kafka_started = True
        st.success("✅ Kafka cluster is running and ready!")
    else:
        st.error("❌ Failed to start Kafka. Please verify configuration.")
else:
    st.success("✅ Kafka already running.")


# --- Import Producer & Consumer ---
from producer import produce_news, get_company_news
from consumer import consume_news


# --- Sidebar Chatbot ---
st.sidebar.header("Chatbot")
st.sidebar.caption(f"Local model: {OLLAMA_MODEL}")

user_prompt = st.sidebar.chat_input("Ask about the dashboard or headlines")
if user_prompt:
    with st.sidebar.chat_message("user"):
        st.markdown(user_prompt)
    with st.sidebar.chat_message("assistant"):
        with st.spinner("Thinking..."):
            company_from_chat = extract_company_from_prompt(user_prompt)
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
                messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}]
                reply = ollama_chat(messages)
            st.markdown(reply)


# --- Company Input ---
company = st.text_input("Enter Company Name:", "Tesla")

# --- Single Unified Button ---
start_btn = st.button("🚀 Start Analysis")

# --- Start both Producer + Consumer together ---
if start_btn:
    st.success(f"Starting full sentiment analysis pipeline for {company}...")

    # Run producer in background
    producer_thread = threading.Thread(target=produce_news, args=(company,), daemon=True)
    producer_thread.start()

    # Run consumer live updates
    st.info("📊 Fetching live sentiment updates...")
    placeholder = st.empty()

    for counts, most_pos, most_neg, overall, conf, all_headlines in consume_news():
        with placeholder.container():
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.markdown(f"### 🕒 Live Sentiment Summary for **{company}** (Updated: `{current_time}`)") 
            
            # Display total news analyzed
            total_news = sum(counts.values())
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📰 Total News Analyzed", total_news)
            with col2:
                st.metric("Overall Sentiment", overall.upper(), f"{conf:.1f}% confidence")

            st.write("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("😊 Positive", counts["positive"], 
                     f"{counts['positive']/total_news*100:.1f}%" if total_news > 0 else "0%")
            c2.metric("☹️ Negative", counts["negative"],
                     f"{counts['negative']/total_news*100:.1f}%" if total_news > 0 else "0%")
            c3.metric("😐 Neutral", counts["neutral"],
                     f"{counts['neutral']/total_news*100:.1f}%" if total_news > 0 else "0%")

            st.write("---")
            st.subheader("Top Headlines")
            st.write(f"**Most Positive:** {most_pos['headline']} *(score={most_pos['score']:.2f})*")
            st.write(f"**Most Negative:** {most_neg['headline']} *(score={most_neg['score']:.2f})*")

            # Display all headlines with sentiment
            st.write("---")
            st.subheader(f"📋 All {len(all_headlines)} Headlines (Sorted by Sentiment)")
            
            for idx, item in enumerate(all_headlines, 1):
                sentiment_emoji = {
                    "positive": "😊",
                    "negative": "☹️",
                    "neutral": "😐"
                }
                emoji = sentiment_emoji.get(item["sentiment"], "")
                score_color = "green" if item["score"] > 0 else "red" if item["score"] < 0 else "gray"
                
                st.markdown(
                    f"{idx}. {emoji} **{item['sentiment'].upper()}** "
                    f"(:{score_color}[score: {item['score']:.3f}]) - {item['headline']}"
                )

            # Small delay to keep UI responsive and update time regularly
            time.sleep(2)
