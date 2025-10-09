# consumer.py
from kafka import KafkaConsumer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import json
import time
from datetime import datetime

TOPIC = "financial-news"
vader = SentimentIntensityAnalyzer()


def analyze_sentiment(text):
    score = vader.polarity_scores(text)["compound"]
    if score >= 0.05:
        sentiment = "positive"
    elif score <= -0.05:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    return sentiment, score


def get_summary(messages):
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    most_pos, most_neg = {"headline": "",
                          "score": -1}, {"headline": "", "score": 1}
    total_score = 0

    for msg in messages:
        headline = msg["headline"]
        sentiment, score = analyze_sentiment(headline)
        counts[sentiment] += 1
        total_score += score

        if score > most_pos["score"]:
            most_pos = {"headline": headline, "score": score}
        if score < most_neg["score"]:
            most_neg = {"headline": headline, "score": score}

    total = sum(counts.values())
    if total == 0:
        return counts, most_pos, most_neg, "neutral", 0

    overall = "positive" if total_score > 0 else "negative" if total_score < 0 else "neutral"
    confidence = abs(total_score / total) * 100
    return counts, most_pos, most_neg, overall, confidence


def consume_news():
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers="localhost:9092",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=False
    )

    buffer = []
    for msg in consumer:
        buffer.append(msg.value)
        if len(buffer) >= 5:  # update summary every few messages
            yield get_summary(buffer)
            buffer = []
        time.sleep(5)
