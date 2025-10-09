# app.py
import streamlit as st
import threading
from producer import produce_news
from consumer import consume_news

st.set_page_config(
    page_title="Financial News Sentiment Dashboard", layout="wide")
st.title("💹 Financial News Sentiment Dashboard")
st.caption("Real-time news sentiment analysis using Kafka + VADER")

# Company Input
company = st.text_input("Enter Company Name:", "Tesla")

# Buttons
col1, col2 = st.columns(2)
start_btn = col1.button("🚀 Start Producer")
consume_btn = col2.button("📊 Start Consumer")

if start_btn:
    st.success(f"Started producing news for {company}...")
    thread = threading.Thread(
        target=produce_news, args=(company,), daemon=True)
    thread.start()

if consume_btn:
    st.info("Fetching live sentiment updates...")
    placeholder = st.empty()

    for counts, most_pos, most_neg, overall, conf in consume_news():
        with placeholder.container():
            st.markdown(
                f"### 🕒 Updated at: `{st.session_state.get('last_time', 'now')}`")
            st.metric("Overall Sentiment", overall.upper(),
                      f"{conf:.1f}% confidence")

            st.write("---")
            col1, col2, col3 = st.columns(3)
            col1.metric("😊 Positive", counts["positive"])
            col2.metric("☹️ Negative", counts["negative"])
            col3.metric("😐 Neutral", counts["neutral"])

            st.write("---")
            st.subheader("Top Headlines")
            st.write(
                f"**Most Positive:** {most_pos['headline']} *(score={most_pos['score']:.2f})*")
            st.write(
                f"**Most Negative:** {most_neg['headline']} *(score={most_neg['score']:.2f})*")
