# 💹 Financial News Sentiment Analysis using Kafka and AI

## 🧠 What It Is
This project analyzes real-time financial news headlines to determine overall **market sentiment** — whether it’s **positive**, **negative**, or **neutral**.  
It uses **Apache Kafka** for streaming live news data from Google News RSS feeds and **VADER (NLP model)** for sentiment classification.  
The system consists of a **Kafka Producer** (fetching news), a **Kafka Consumer** (analyzing sentiment), and an optional **Streamlit Dashboard** for visualization.  

---

## ⚙️ How to Run

### **1️⃣ Prerequisites**
- Python 3.9+  
- Apache Kafka installed locally  
- Internet connection for fetching RSS feeds  

Install dependencies:
```bash
pip install kafka-python vaderSentiment feedparser streamlit
```

---

### **2️⃣ Start Kafka**
Open two terminals and run:
```bash
# Terminal 1: Start Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties
```

```bash
# Terminal 2: Start Kafka Broker
bin/kafka-server-start.sh config/server.properties
```

Then create the topic:
```bash
bin/kafka-topics.sh --create --topic financial-news --bootstrap-server localhost:9092
```

---

### **3️⃣ Run the Producer**
Fetches live financial news and sends headlines to the Kafka topic.
```bash
python KafkaProducer.py
```

---

### **4️⃣ Run the Consumer**
Consumes messages from the topic, performs sentiment analysis, and displays overall sentiment with confidence.
```bash
python KafkaConsumer.py
```

---

### **5️⃣ (Optional) Run the Dashboard**
Visualizes real-time sentiment summary in the browser.
```bash
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

✅ **Now your app will stream real financial headlines, analyze their sentiment, and show live updates!**
