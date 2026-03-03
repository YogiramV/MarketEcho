const companyInput = document.getElementById("companyInput");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const statusMessage = document.getElementById("statusMessage");
const pipelineStatus = document.getElementById("pipelineStatus");

const totalNews = document.getElementById("totalNews");
const overallSentiment = document.getElementById("overallSentiment");
const confidence = document.getElementById("confidence");
const positiveCount = document.getElementById("positiveCount");
const negativeCount = document.getElementById("negativeCount");
const neutralCount = document.getElementById("neutralCount");
const mostPositive = document.getElementById("mostPositive");
const mostNegative = document.getElementById("mostNegative");
const headlinesList = document.getElementById("headlinesList");

const chatHistory = document.getElementById("chatHistory");
const chatInput = document.getElementById("chatInput");
const chatSend = document.getElementById("chatSend");

function setMessage(text, isError = false) {
    statusMessage.textContent = text;
    statusMessage.style.color = isError ? "#f87171" : "#9ca3af";
}

function appendChat(role, text) {
    const item = document.createElement("div");
    item.className = `chat-msg ${role}`;
    item.textContent = text;
    chatHistory.appendChild(item);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function formatHeadline(item) {
    const score = Number(item.score || 0).toFixed(3);
    return `${item.sentiment.toUpperCase()} [${score}] - ${item.headline}`;
}

async function startPipeline() {
    const company = companyInput.value.trim();
    if (!company) {
        setMessage("Company name is required.", true);
        return;
    }

    startBtn.disabled = true;
    setMessage("Starting pipeline...");

    try {
        const res = await fetch("/api/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ company })
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
            throw new Error(data.error || "Failed to start pipeline.");
        }
        setMessage(data.message || "Pipeline started.");
    } catch (err) {
        setMessage(err.message, true);
    } finally {
        startBtn.disabled = false;
    }
}

async function stopPipeline() {
    stopBtn.disabled = true;
    try {
        const res = await fetch("/api/stop", { method: "POST" });
        const data = await res.json();
        if (!res.ok || !data.ok) {
            throw new Error(data.error || "Failed to stop pipeline.");
        }
        setMessage(data.message || "Pipeline stopped.");
    } catch (err) {
        setMessage(err.message, true);
    } finally {
        stopBtn.disabled = false;
    }
}

async function sendChat() {
    const prompt = chatInput.value.trim();
    if (!prompt) return;

    appendChat("user", prompt);
    chatInput.value = "";
    chatSend.disabled = true;

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt })
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
            throw new Error(data.error || "Chat request failed.");
        }
        appendChat("assistant", data.reply || "No response");
    } catch (err) {
        appendChat("assistant", `Error: ${err.message}`);
    } finally {
        chatSend.disabled = false;
    }
}

async function pollStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        if (!res.ok || !data.ok) return;

        pipelineStatus.textContent = data.running
            ? `Running • ${data.company || "-"}`
            : "Idle";
        pipelineStatus.style.borderColor = data.running ? "#16a34a" : "#374151";

        const summary = data.summary || {};
        const counts = summary.counts || {};

        totalNews.textContent = summary.total_news || 0;
        overallSentiment.textContent = (summary.overall || "neutral").toUpperCase();
        confidence.textContent = `${Number(summary.confidence || 0).toFixed(2)}%`;

        positiveCount.textContent = counts.positive || 0;
        negativeCount.textContent = counts.negative || 0;
        neutralCount.textContent = counts.neutral || 0;

        const pos = summary.most_positive || {};
        const neg = summary.most_negative || {};

        mostPositive.textContent = pos.headline
            ? `${pos.headline} (score=${Number(pos.score).toFixed(3)})`
            : "—";
        mostNegative.textContent = neg.headline
            ? `${neg.headline} (score=${Number(neg.score).toFixed(3)})`
            : "—";

        const headlines = summary.headlines || [];
        headlinesList.innerHTML = "";
        for (const item of headlines) {
            const li = document.createElement("li");
            li.textContent = formatHeadline(item);
            headlinesList.appendChild(li);
        }

        if (data.error) {
            setMessage(data.error, true);
        }
    } catch (err) {
        setMessage(`Status error: ${err.message}`, true);
    }
}

startBtn.addEventListener("click", startPipeline);
stopBtn.addEventListener("click", stopPipeline);
chatSend.addEventListener("click", sendChat);
chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendChat();
    }
});

pollStatus();
setInterval(pollStatus, 2000);
