# consumer.py
from kafka import KafkaConsumer
import json
import time
from datetime import datetime

TOPIC = "financial-news"

# Initialize FinBERT for CPU usage
try:
    from transformers import pipeline
    import torch

    # Force CPU usage and optimize for low-end hardware
    device = torch.device('cpu')

    # Use FinBERT with CPU optimizations
    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model="ProsusAI/finbert",
        device=device,
        torch_dtype=torch.float32,  # Use float32 for CPU
        return_all_scores=False,
        truncation=True,
        max_length=512
    )

    USE_FINBERT = True
    print("✅ FinBERT loaded successfully for CPU usage")

except ImportError as e:
    print(f"❌ Failed to load transformers/torch: {e}")
    USE_FINBERT = False
    sentiment_pipeline = None

except Exception as e:
    print(f"❌ Failed to load FinBERT model: {e}")
    USE_FINBERT = False
    sentiment_pipeline = None


def analyze_sentiment(text):
    if not USE_FINBERT or sentiment_pipeline is None:
        raise Exception("FinBERT is not available. Please ensure transformers and torch are installed.")

    try:
        # Run inference on CPU
        result = sentiment_pipeline(text)[0]
        sentiment = result['label'].lower()
        score = result['score']

        # Normalize score
        if sentiment == 'positive':
            score = score
        elif sentiment == 'negative':
            score = -score
        else:
            score = 0

        return sentiment, score

    except Exception as e:
        raise Exception(f"FinBERT analysis failed: {e}. FinBERT is required for this application.")


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
