import streamlit as st
import importlib.util
import threading
import os
import time
from datetime import datetime

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
from producer import produce_news
from consumer import consume_news


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
