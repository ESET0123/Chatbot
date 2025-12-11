// GLOBALS
let conversations = {};
let currentConversationId = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let authToken = null;
let currentUser = null;
let isProcessingMessage = false; // Prevent concurrent requests

const messagesContainer = document.getElementById("messages");
const suggestionsBox = document.getElementById("suggestionsBox");
const voiceBtn = document.getElementById("voiceBtn");
const userInput = document.getElementById("userInput");
const API_URL = "http://127.0.0.1:8000";

let speechRecognition = null;

// DEBUG HELPER
function debugLog(message, data = null, holdTime = 0) {
  console.log(`[DEBUG] ${message}`, data || '');
  if (holdTime > 0) {
    console.log(`[DEBUG] Holding for ${holdTime}ms...`);
    return new Promise(resolve => setTimeout(resolve, holdTime));
  }
}

// PREVENT ALL NAVIGATION DURING MESSAGE PROCESSING
window.addEventListener('beforeunload', (e) => {
  if (isProcessingMessage) {
    e.preventDefault();
    // e.returnValue = 'A message is being processed. Are you sure you want to leave?';
    debugLog('⚠️ BEFOREUNLOAD EVENT - Message processing in progress!');
    return e.returnValue;
  }
});

// Prevent all forms from submitting
document.addEventListener('submit', (e) => {
  debugLog('⚠️ FORM SUBMIT EVENT CAUGHT AND PREVENTED!');
  e.preventDefault();
  e.stopPropagation();
  return false;
}, true);

// Check authentication on load
window.onload = async () => {
  await debugLog('🚀 Page loaded, starting authentication check', null, 1000);
  await checkAuth();
  await debugLog('✅ Auth check complete', null, 1000);
  loadConversationList();
  initBrowserSpeechRecognition();
};

// Check if user is authenticated
async function checkAuth() {
  await debugLog('🔐 Starting checkAuth()');
  authToken = sessionStorage.getItem('token');
  const userJson = sessionStorage.getItem('user');
  
  await debugLog('Token from storage:', authToken, 1000);
  await debugLog('User from storage:', userJson, 1000);
  
  if (!authToken || !userJson) {
    await debugLog('❌ No token or user found, redirecting to login', null, 2000);
    window.location.href = './../backend/auth.html';
    return;
  }
  
  currentUser = JSON.parse(userJson);
  await debugLog('👤 Current user parsed:', currentUser, 1000);
  
  // Verify token is still valid
  try {
    await debugLog('🌐 Verifying token with /auth/me', null, 1000);
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
    
    await debugLog('Response status:', res.status, 1000);
    
    if (!res.ok) {
      throw new Error('Invalid token');
    }
    
    const userData = await res.json();
    await debugLog('✅ Token verified, user data:', userData, 1000);
    
    // Update email display
    document.getElementById('nameDisplay').textContent = currentUser.name;
    document.getElementById('emailDisplay').textContent = currentUser.email;
    
  } catch (error) {
    await debugLog('❌ Auth verification failed:', error, 2000);
    console.error('Auth check failed:', error);
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('user');
    window.location.href = './../backend/auth.html';
  }
}

// Logout
document.getElementById('logoutBtn').addEventListener('click', async (e) => {
  e.preventDefault();
  e.stopPropagation();
  await debugLog('🚪 Logout clicked', null, 1000);
  sessionStorage.removeItem('token');
  sessionStorage.removeItem('user');
  window.location.href = './../backend/auth.html';
});

// Initialize browser speech recognition
function initBrowserSpeechRecognition() {
  debugLog('🎤 Initializing speech recognition');
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
document.getElementById("newChatBtn").onclick = async (e) => {
  e.preventDefault();
  e.stopPropagation();
  await debugLog('➕ New chat button clicked', null, 500);
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
  await debugLog('📤 sendMessage() called with text:', text, 1000);
  
  if (!text || !text.trim()) {
    await debugLog('⚠️ Empty text, returning', null, 500);
    return;
  }

  if (isProcessingMessage) {
    await debugLog('⚠️ Already processing a message, ignoring', null, 500);
    return;
  }

  isProcessingMessage = true;
  await debugLog('🔒 Message processing LOCKED', null, 500);

  if (!currentConversationId) {
    await debugLog('🆕 No conversation ID, creating new one', null, 1000);
    const id = "conv_" + Date.now();
    conversations[id] = { messages: [] };
    currentConversationId = id;
    loadConversationList();
  }

  await debugLog('💬 Current conversation ID:', currentConversationId, 1000);
  
  const context = getConversationContext(currentConversationId);
  await debugLog('📋 Context retrieved:', context, 1000);
  
  const userMessageIndex = conversations[currentConversationId].messages.length;
  appendMessage(text, "user", true, false, false, null, null);
  suggestionsBox.classList.add("hidden");

  await debugLog('⏳ Showing loading indicator', null, 500);
  showLoading();

  try {
    await debugLog('🌐 About to fetch /ask endpoint', null, 2000);
    await debugLog('🔑 Using token:', authToken?.substring(0, 20) + '...', 1000);
    await debugLog('📦 Request payload:', { query: text, conversation_id: currentConversationId }, 2000);
    
    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      debugLog('⏰ Request timeout after 60 seconds');
      controller.abort();
    }, 60000);

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
      }),
      signal: controller.signal
    });

    clearTimeout(timeoutId);
    await debugLog('📥 Response received, status:', res.status, 2000);

    if (res.status === 401) {
      await debugLog('❌ 401 Unauthorized - session expired', null, 2000);
      hideLoading();
      appendMessage("Session expired. Please login again.", "bot");
      isProcessingMessage = false;
      await debugLog('⏰ Waiting 3 seconds before redirect...', null, 3000);
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('user');
      window.location.href = './../backend/auth.html';
      return;
    }

    await debugLog('📋 Parsing response JSON...', null, 1000);
    const data = await res.json();
    await debugLog('✅ Response data:', data, 3000);
    
    hideLoading();

    if (data.sql && conversations[currentConversationId]) {
      await debugLog('💾 Saving SQL to conversation history:', data.sql, 1000);
      conversations[currentConversationId].messages[userMessageIndex].sql = data.sql;
      saveAll();
    }

    if (data.result && data.result.error) {
      await debugLog('❌ SQL error:', data.result.error, 2000);
      appendMessage(`Error: ${data.result.error}`, "bot");
      isProcessingMessage = false;
      await debugLog('🔓 Message processing UNLOCKED', null, 500);
      return;
    }

    if (data.response_type === "chart" && data.chart) {
      await debugLog('📊 Rendering chart response', null, 1000);
      appendMessage("", "bot", true, false, true, data.chart);
      isProcessingMessage = false;
      await debugLog('🔓 Message processing UNLOCKED', null, 500);
      return;
    }

    if (!data.result || !data.result.rows || data.result.rows.length === 0) {
      await debugLog('⚠️ No data found in response', null, 1000);
      appendMessage("No data found.", "bot");
      isProcessingMessage = false;
      await debugLog('🔓 Message processing UNLOCKED', null, 500);
      return;
    }

    await debugLog('📊 Building table HTML...', null, 1000);
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

    await debugLog('✅ Appending table to UI', null, 1000);
    appendMessage(tableHTML, "bot", true, true);
    await debugLog('🎉 Message send complete!', null, 2000);

  } catch (error) {
    await debugLog('💥 FETCH ERROR:', error, 5000);
    hideLoading();
    console.error(error);
    
    if (error.name === 'AbortError') {
      appendMessage("Request timed out. Please try again.", "bot");
    } else {
      appendMessage("Connection error. Please check if the server is running.", "bot");
    }
  } finally {
    isProcessingMessage = false;
    await debugLog('🔓 Message processing UNLOCKED (finally block)', null, 500);
  }
}

document.getElementById("sendBtn").onclick = async (e) => {
  e.preventDefault();
  e.stopPropagation();
  await debugLog('🖱️ Send button clicked', null, 500);
  const text = userInput.value.trim();
  userInput.value = "";
  await sendMessage(text);
};

// Voice input
voiceBtn.onclick = (e) => {
  e.preventDefault();
  e.stopPropagation();
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
  btn.onclick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    userInput.value = btn.innerText;
    document.getElementById("sendBtn").click();
  };
});

// Enter key
userInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById("sendBtn").click();
  }
});

// Sidebar toggle
document.getElementById("toggleSidebar").onclick = (e) => {
  e.preventDefault();
  e.stopPropagation();
  document.getElementById("sidebar").classList.toggle("collapsed");
};

// Theme toggle
document.getElementById("themeToggle").onclick = (e) => {
  e.preventDefault();
  e.stopPropagation();
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

// Additional page unload protection
window.addEventListener('pagehide', () => {
  debugLog('⚠️ PAGEHIDE EVENT FIRED');
});

window.addEventListener('unload', () => {
  debugLog('⚠️ UNLOAD EVENT FIRED');
});