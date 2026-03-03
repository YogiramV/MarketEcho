# MarketEcho: Real-Time Financial Sentiment Dashboard

MarketEcho analyzes live financial headlines and classifies sentiment as positive, negative, or neutral.
It uses Kafka for streaming, FinBERT for sentiment inference, and a Flask web UI for visualization.

## Architecture
- Producer (`producer.py`): fetches company-related RSS headlines and publishes to Kafka topic `financial-news`
- Consumer (`consumer.py`): consumes headlines and computes rolling sentiment summary with FinBERT
- Web App (`app.py`): Flask backend + professional dashboard UI (`templates/`, `static/`)
- Kafka Bootstrap (`start_kafka.py`): starts local Kafka (KRaft mode) if not already running

## Prerequisites
- Python 3.9+
- Local Kafka distribution (already included in this project)
- Internet connection for RSS headline fetch

## Install
```bash
pip install -r requirements.txt
```

FinBERT model files are downloaded automatically on first run.

## Run the Application
```bash
python app.py
```

Then open:
- http://localhost:5000

## Features
- Start/stop sentiment pipeline per company
- Live metrics (total headlines, sentiment breakdown, overall confidence)
- Most positive and most negative headlines
- Sorted headline list by sentiment score
- Integrated assistant panel (Ollama-based chat)

## Optional Environment Variables
- `OLLAMA_HOST` (default: `http://localhost:11434`)
- `OLLAMA_MODEL` (default: `llama3.2:1b`)

## Notes
- Kafka starts automatically when you click **Start** in the UI.
- If Ollama is unavailable, chat requests return an informative error message.
