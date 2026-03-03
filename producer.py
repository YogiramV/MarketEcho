# producer.py
import feedparser
from kafka import KafkaProducer
import json
import time
from urllib.parse import quote_plus

TOPIC = "financial-news"

producer = None


def get_producer():
    global producer
    if producer is None:
        producer = KafkaProducer(
            bootstrap_servers="localhost:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
    return producer


def get_company_news(company):
    """Fetch company-specific finance news via RSS."""
    query = quote_plus(f"{company} finance")
    url = f"https://news.google.com/rss/search?q={query}"
    feed = feedparser.parse(url)
    return [entry.title for entry in feed.entries]


def produce_news(company, stop_event=None, interval_seconds=60):
    """Continuously fetch & send news to Kafka.

    Args:
        company: Company name to fetch headlines for.
        stop_event: Optional threading.Event to stop production gracefully.
        interval_seconds: Delay between fetch cycles.
    """
    print(f"🔎 Fetching news for {company}...")
    seen = set()
    kafka_producer = get_producer()

    while True:
        if stop_event is not None and stop_event.is_set():
            print(f"🛑 Stopping producer for {company}")
            break

        news_items = get_company_news(company)
        for news in news_items:
            if news not in seen:
                msg = {"company": company, "headline": news}
                kafka_producer.send(TOPIC, msg)
                print(f"Produced: {msg}")
                seen.add(news)

            kafka_producer.flush()

        if stop_event is None:
            time.sleep(interval_seconds)
        else:
            stop_event.wait(interval_seconds)
