# 💹 Financial News Sentiment Analysis using Kafka and AI

## 🧠 What It Is
This project analyzes **real-time financial news headlines** to determine overall **market sentiment** — whether it’s **positive**, **negative**, or **neutral**.  
It leverages **Apache Kafka (KRaft mode)** for real-time data streaming and **FinBERT (CPU-optimized)** for financial sentiment classification.  
The architecture includes:
- **Kafka Producer** → Fetches live company-related news headlines.  
- **Kafka Consumer** → Performs real-time sentiment aggregation.  
- **Streamlit Dashboard** → Displays live market mood and sentiment metrics.

---

## ⚙️ How to Run

### **1️⃣ Prerequisites**
- **Python 3.9+**
- **Apache Kafka 2.13–4.1.0** installed locally  
- **Internet connection** for fetching RSS feeds  

Install dependencies:
```bash
pip install -r requirements.txt
```

### **1.5️⃣ Model Download**
The first time you run the application, FinBERT model (~400MB) will be downloaded automatically. This only happens once and runs on CPU for low-end hardware compatibility.

---

### **2️⃣ Start Kafka Automatically (Recommended)**
Simply run the dashboard — Kafka will start automatically via the `start_kafka.py` script:

```bash
streamlit run app.py
```

✅ This script:
- Checks if Kafka is already running  
- Formats and initializes storage (only once)  
- Starts Kafka Broker automatically in **KRaft mode**  
- Waits until it’s ready before launching the app  

---

### **3️⃣ Manual Kafka Startup (Alternative)**
If you prefer to start Kafka manually instead of auto-start:

```bash
# Step 1: Generate a new Cluster ID (only first time)
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"

# Step 2: Format storage for KRaft mode
bin/kafka-storage.sh format --standalone -t $KAFKA_CLUSTER_ID -c config/server.properties

# Step 3: Start the Kafka Broker
bin/kafka-server-start.sh config/server.properties
```

---

### **4️⃣ Run the Producer**
The producer fetches **financial news headlines** from Google News RSS feeds for specified companies and sends them to the Kafka topic `financial-news`.

```bash
python KafkaProducer.py
```

---

### **5️⃣ Run the Consumer**
The consumer listens to the same topic, applies **FinBERT sentiment analysis**, and provides:
- Sentiment distribution (Positive / Negative / Neutral)  
- Overall sentiment label and confidence  
- Most positive and most negative headlines  

```bash
python KafkaConsumer.py
```

---

### **6️⃣ (Optional) Streamlit Dashboard**
Run this for a live UI view of market sentiment:

```bash
streamlit run app.py
```

Then open the dashboard at:  
👉 [http://localhost:8501](http://localhost:8501)

The dashboard lets you:
- Enter a company name (e.g., Tesla, Apple)  
- Start/stop producer and consumer streams  
- View live positive, negative, and neutral counts  
- See the most extreme headlines and sentiment confidence  

---

### ✅ **End-to-End Flow**
1. Kafka auto-starts (KRaft mode).  
2. Producer streams live financial headlines.  
3. Consumer performs continuous NLP sentiment analysis.  
4. Streamlit dashboard visualizes real-time sentiment.  

---

### 🧩 Tech Stack
- **Apache Kafka 4.1.0** (KRaft mode)
- **Python 3.9+**
- **FinBERT** (CPU-optimized financial sentiment model)
- **Feedparser (Google News RSS)**
- **Streamlit (Interactive UI)**

---

✅ **Now your app will stream real financial headlines, analyze their sentiment, and show live updates — all in real time using Kafka and AI!**
