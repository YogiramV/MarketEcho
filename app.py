# app.py
import streamlit as st
import importlib.util
import threading
import os

# --- Dynamically import start_kafka.py no matter what ---
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

# Only start Kafka once per session
if "kafka_started" not in st.session_state:
    st.info("🔍 Checking Kafka cluster status...")
    if load_and_start_kafka():
        st.session_state.kafka_started = True
        st.success("✅ Kafka cluster is running and ready!")
    else:
        st.error("❌ Failed to start Kafka. Please verify configuration.")
else:
    st.success("✅ Kafka already running.")

# Continue with your rest of Streamlit logic (producer/consumer)
from producer import produce_news
from consumer import consume_news

company = st.text_input("Enter Company Name:", "Tesla")

col1, col2 = st.columns(2)
start_btn = col1.button("🚀 Start Producer")
consume_btn = col2.button("📊 Start Consumer")

if start_btn:
    st.success(f"Started producing news for {company}...")
    thread = threading.Thread(target=produce_news, args=(company,), daemon=True)
    thread.start()

if consume_btn:
    st.info("Fetching live sentiment updates...")
    placeholder = st.empty()

    for counts, most_pos, most_neg, overall, conf in consume_news():
        with placeholder.container():
            st.markdown("### 🕒 Updated Sentiment Summary")
            st.metric("Overall Sentiment", overall.upper(), f"{conf:.1f}% confidence")
            st.write("---")
            col1, col2, col3 = st.columns(3)
            col1.metric("😊 Positive", counts["positive"])
            col2.metric("☹️ Negative", counts["negative"])
            col3.metric("😐 Neutral", counts["neutral"])
            st.write("---")
            st.subheader("Top Headlines")
            st.write(f"**Most Positive:** {most_pos['headline']} *(score={most_pos['score']:.2f})*")
            st.write(f"**Most Negative:** {most_neg['headline']} *(score={most_neg['score']:.2f})*")
