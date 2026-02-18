# producer.py
import feedparser
from kafka import KafkaProducer
import json
import time
from urllib.parse import quote_plus

TOPIC = "financial-news"

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)


def get_company_news(company):
    """Fetch company-specific finance news via RSS."""
    query = quote_plus(f"{company} finance")
    url = f"https://news.google.com/rss/search?q={query}"
    feed = feedparser.parse(url)
    return [entry.title for entry in feed.entries]


def produce_news(company):
    """Continuously fetch & send news to Kafka."""
    print(f"🔎 Fetching news for {company}...")
    seen = set()
    while True:
        news_items = get_company_news(company)
        for news in news_items:
            if news not in seen:
                msg = {"company": company, "headline": news}
                producer.send(TOPIC, msg)
                print(f"Produced: {msg}")
                seen.add(news)
        producer.flush()
        time.sleep(60)  # fetch every minute
