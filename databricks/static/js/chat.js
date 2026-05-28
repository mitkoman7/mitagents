// DXC Databricks Assistant - Chat JS

const messagesContainer = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");
const typingIndicator = document.getElementById("typingIndicator");
const statusBar = document.getElementById("statusBar");

let isWaiting = false;

// Check MCP health on load
async function checkHealth() {
    try {
        const res = await fetch("/api/health");
        const data = await res.json();
        if (data.mcp_connected) {
            statusBar.textContent = "MCP Server Connected";
            statusBar.className = "status-bar connected";
        } else {
            statusBar.textContent = "MCP Server Disconnected - start mcp_server.py first";
            statusBar.className = "status-bar disconnected";
        }
    } catch {
        statusBar.textContent = "Backend not reachable";
        statusBar.className = "status-bar disconnected";
    }
}

function getTimeStr() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatMessage(text) {
    // Convert markdown-style code blocks
    let formatted = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code>${escapeHtml(code.trim())}</code></pre>`;
    });
    // Inline code
    formatted = formatted.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Bold
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    // Line breaks (but not inside <pre>)
    const parts = formatted.split(/(<pre>[\s\S]*?<\/pre>)/g);
    formatted = parts
        .map((p) => (p.startsWith("<pre>") ? p : p.replace(/\n/g, "<br>")))
        .join("");
    return formatted;
}

function addMessage(text, sender) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${sender}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = sender === "bot" ? "\uD83E\uDD16" : "\uD83D\uDC64";

    const bubble = document.createElement("div");
    bubble.className = "message-content";
    bubble.innerHTML = sender === "bot" ? formatMessage(text) : escapeHtml(text);

    const time = document.createElement("div");
    time.className = "message-time";
    time.textContent = getTimeStr();

    const col = document.createElement("div");
    col.appendChild(bubble);
    col.appendChild(time);

    wrapper.appendChild(avatar);
    wrapper.appendChild(col);

    messagesContainer.appendChild(wrapper);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showTyping() {
    typingIndicator.classList.add("visible");
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideTyping() {
    typingIndicator.classList.remove("visible");
}

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || isWaiting) return;

    addMessage(text, "user");
    chatInput.value = "";
    isWaiting = true;
    sendBtn.disabled = true;
    showTyping();

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text }),
        });
        const data = await res.json();
        hideTyping();
        addMessage(data.reply || data.error || "No response", "bot");
    } catch (err) {
        hideTyping();
        addMessage("Connection error. Is the server running?", "bot");
    } finally {
        isWaiting = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

async function clearChat() {
    try {
        await fetch("/api/clear", { method: "POST" });
    } catch {}
    // Remove all messages except the welcome
    messagesContainer.innerHTML = "";
    addWelcomeMessage();
}

function addWelcomeMessage() {
    addMessage(
        "Hello! I'm your DXC Databricks Assistant.\nAsk me about databases, tables, clusters, jobs, notebooks and more!",
        "bot"
    );
}

// Events
sendBtn.addEventListener("click", sendMessage);

chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

clearBtn.addEventListener("click", clearChat);

// Init
checkHealth();
addWelcomeMessage();
chatInput.focus();
