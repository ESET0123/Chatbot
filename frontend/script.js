// GLOBALS
let conversations = {};
let currentConversationId = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let authToken = null;
let currentUser = null;

const messagesContainer = document.getElementById("messages");
const suggestionsBox = document.getElementById("suggestionsBox");
const voiceBtn = document.getElementById("voiceBtn");
const userInput = document.getElementById("userInput");
const API_URL = "http://127.0.0.1:8000";

let speechRecognition = null;

// Check authentication on load
window.onload = async () => {
  await checkAuth();
  loadConversationList();
  initBrowserSpeechRecognition();
};

// Check if user is authenticated
async function checkAuth() {
  authToken = sessionStorage.getItem('token');
  const userJson = sessionStorage.getItem('user');
  
  if (!authToken || !userJson) {
    window.location.href = './../backend/auth.html';
    return;
  }
  
  currentUser = JSON.parse(userJson);
  // console.log("test4", currentUser)
  
  // Verify token is still valid
  try {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
    
    if (!res.ok) {
      throw new Error('Invalid token');
    }
    
    // Update email display
    document.getElementById('nameDisplay').textContent = currentUser.name;
    document.getElementById('emailDisplay').textContent = currentUser.email;
    
  } catch (error) {
    console.error('Auth check failed:', error);
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('user');
    window.location.href = './../backend/auth.html';
  }
}

// Logout
document.getElementById('logoutBtn').addEventListener('click', () => {
  sessionStorage.removeItem('token');
  sessionStorage.removeItem('user');
  window.location.href = './../backend/auth.html';
});

// Initialize browser speech recognition
function initBrowserSpeechRecognition() {
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    speechRecognition = new SpeechRecognition();
    
    speechRecognition.continuous = false;
    speechRecognition.interimResults = false;
    speechRecognition.lang = 'en-US';
    speechRecognition.maxAlternatives = 1;
    
    speechRecognition.onstart = () => {
      isRecording = true;
      voiceBtn.classList.add("recording");
      voiceBtn.innerText = "⏹️";
    };
    
    speechRecognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      userInput.value = transcript;
      userInput.focus();
    };
    
    speechRecognition.onerror = (event) => {
      let errorMessage = "Speech recognition error";
      switch(event.error) {
        case 'no-speech':
          errorMessage = "No speech detected. Please try again.";
          break;
        case 'audio-capture':
          errorMessage = "No microphone found.";
          break;
        case 'not-allowed':
          errorMessage = "Microphone access denied.";
          break;
      }
      appendMessage(errorMessage, "bot");
    };
    
    speechRecognition.onend = () => {
      isRecording = false;
      voiceBtn.classList.remove("recording");
      voiceBtn.innerText = "🎤";
    };
  }
}

function saveAll() {
  console.log("Conversations saved in memory");
}

function getConversationContext(conversationId) {
  if (!conversationId || !conversations[conversationId]) {
    return [];
  }
  
  const messages = conversations[conversationId].messages;
  const context = [];
  
  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    if (msg.type === "user" && msg.sql) {
      context.push({
        query: msg.text,
        sql: msg.sql
      });
    }
  }
  
  return context.slice(-7);
}

// Create new conversation
document.getElementById("newChatBtn").onclick = () => {
  const id = "conv_" + Date.now();
  conversations[id] = { messages: [] };
  currentConversationId = id;
  saveAll();
  loadConversationList();
  messagesContainer.innerHTML = "";
  suggestionsBox.classList.remove("hidden");
  
  if (speechRecognition && isRecording) {
    speechRecognition.stop();
  }
};

// Load conversation list
function loadConversationList() {
  const list = document.getElementById("conversationList");
  list.innerHTML = "";

  Object.keys(conversations).forEach(id => {
    const div = document.createElement("div");
    div.className = "conversation-item";
    const firstMsg = conversations[id].messages.find(m => m.type === "user");
    div.innerText = firstMsg ? firstMsg.text.substring(0, 30) + "..." : "New Chat";
    div.onclick = () => loadConversation(id);
    list.appendChild(div);
  });
}

// Load conversation messages
function loadConversation(id) {
  currentConversationId = id;
  messagesContainer.innerHTML = "";

  const msgs = conversations[id].messages;
  msgs.forEach(m => {
    if (m.isChart) {
      appendMessage("", m.type, false, false, true, m.chartConfig, null);
    } else {
      appendMessage(m.text, m.type, false, m.isHTML, false, null, null);
    }
  });

  const hasUserMessage = msgs.some(m => m.type === "user");
  suggestionsBox.classList.toggle("hidden", hasUserMessage);
}

// Append message to UI
function appendMessage(content, type, save = true, isHTML = false, isChart = false, chartConfig = null, sqlQuery = null) {
  const msg = document.createElement("div");
  msg.classList.add("message", type);

  if (isChart && chartConfig) {
    const chartContainer = document.createElement("div");
    chartContainer.className = "chart-container";
    
    const canvas = document.createElement("canvas");
    chartContainer.appendChild(canvas);
    msg.appendChild(chartContainer);
    messagesContainer.appendChild(msg);
    
    new Chart(canvas.getContext("2d"), chartConfig);
  } else if (isHTML) {
    msg.innerHTML = content;
    messagesContainer.appendChild(msg);
  } else {
    msg.innerText = content;
    messagesContainer.appendChild(msg);
  }

  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  if (save && currentConversationId) {
    const messageData = { 
      text: content, 
      type, 
      isHTML, 
      isChart,
      chartConfig: isChart ? chartConfig : null
    };
    
    if (type === "user" && sqlQuery) {
      messageData.sql = sqlQuery;
    }
    
    conversations[currentConversationId].messages.push(messageData);
    saveAll();
  }
}

// Show loading
function showLoading() {
  const loading = document.createElement("div");
  loading.className = "loading";
  loading.id = "loadingIndicator";
  loading.innerHTML = `
    <div class="loading-dot"></div>
    <div class="loading-dot"></div>
    <div class="loading-dot"></div>
  `;
  messagesContainer.appendChild(loading);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Hide loading
function hideLoading() {
  const loading = document.getElementById("loadingIndicator");
  if (loading) loading.remove();
}

// Send message
async function sendMessage(text) {
  if (!text || !text.trim()) return;

  if (!currentConversationId) {
    const id = "conv_" + Date.now();
    conversations[id] = { messages: [] };
    currentConversationId = id;
    loadConversationList();
  }

  const context = getConversationContext(currentConversationId);
  const userMessageIndex = conversations[currentConversationId].messages.length;
  appendMessage(text, "user", true, false, false, null, null);
  suggestionsBox.classList.add("hidden");

  showLoading();

  try {
    const res = await fetch(`${API_URL}/ask`, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${authToken}`
      },
      body: JSON.stringify({ 
        query: text,
        conversation_id: currentConversationId,
        conversation_history: context
      })
    });

    if (res.status === 401) {
      hideLoading();
      appendMessage("Session expired. Please login again.", "bot");
      setTimeout(() => {
        window.location.href = './../backend/auth.html';
      }, 2000);
      // return;
    }

    const data = await res.json();
    hideLoading();

    if (data.sql && conversations[currentConversationId]) {
      conversations[currentConversationId].messages[userMessageIndex].sql = data.sql;
      saveAll();
    }

    if (data.result && data.result.error) {
      appendMessage(`Error: ${data.result.error}`, "bot");
      return;
    }

    if (data.response_type === "chart" && data.chart) {
      appendMessage("", "bot", true, false, true, data.chart);
      return;
    }

    if (!data.result || !data.result.rows || data.result.rows.length === 0) {
      appendMessage("No data found.", "bot");
      return;
    }

    let tableHTML = `
      <div class="table-info">
        <small style="color: #666; display: block; margin-bottom: 8px;">
          ${data.result.rows.length} rows returned
        </small>
      </div>
      <div class="overflow-auto">
        <table>
          <thead>
            <tr>
              ${data.result.columns.map(col => `<th>${col}</th>`).join("")}
            </tr>
          </thead>
          <tbody>
            ${data.result.rows.map(row => `
              <tr>
                ${row.map(cell => `<td>${cell !== null ? cell : ''}</td>`).join("")}
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;

    appendMessage(tableHTML, "bot", true, true);

  } catch (error) {
    hideLoading();
    console.error(error);
    appendMessage("Connection error. Please check if the server is running.", "bot");
  }
}

document.getElementById("sendBtn").onclick = async () => {
  const text = userInput.value.trim();
  userInput.value = "";
  await sendMessage(text);
};

// Voice input
voiceBtn.onclick = () => {
  if (speechRecognition) {
    if (!isRecording) {
      try {
        speechRecognition.start();
      } catch (error) {
        appendMessage("Failed to start voice recognition.", "bot");
      }
    } else {
      speechRecognition.stop();
    }
  }
};

// Suggestion clicks
document.querySelectorAll(".suggest-btn").forEach(btn => {
  btn.onclick = () => {
    userInput.value = btn.innerText;
    document.getElementById("sendBtn").click();
  };
});

// Enter key
userInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter") {
    document.getElementById("sendBtn").click();
  }
});

// Sidebar toggle
document.getElementById("toggleSidebar").onclick = () => {
  document.getElementById("sidebar").classList.toggle("collapsed");
};

// Theme toggle
document.getElementById("themeToggle").onclick = () => {
  const body = document.body;
  const btn = document.getElementById("themeToggle");
  
  if (body.classList.contains("dark")) {
    body.classList.remove("dark");
    body.classList.add("light");
    btn.innerText = "☀️";
  } else {
    body.classList.remove("light");
    body.classList.add("dark");
    btn.innerText = "🌙";
  }
};

// Keyboard shortcut
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === ' ' && !e.repeat) {
    e.preventDefault();
    voiceBtn.click();
  }
});