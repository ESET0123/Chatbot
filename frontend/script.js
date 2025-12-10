// GLOBALS
let conversations = {};
let currentConversationId = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];

const messagesContainer = document.getElementById("messages");
const suggestionsBox = document.getElementById("suggestionsBox");
const voiceBtn = document.getElementById("voiceBtn");
const userInput = document.getElementById("userInput");

// Initialize browser speech recognition
let speechRecognition = null;

// Load saved chats (use in-memory storage instead of localStorage)
window.onload = () => {
  loadConversationList();
  initBrowserSpeechRecognition();
};

// Initialize browser's built-in speech recognition
function initBrowserSpeechRecognition() {
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    speechRecognition = new SpeechRecognition();
    
    speechRecognition.continuous = false;
    speechRecognition.interimResults = false;
    speechRecognition.lang = 'en-US';
    speechRecognition.maxAlternatives = 1;
    
    // Event handlers for speech recognition
    speechRecognition.onstart = () => {
      console.log("Speech recognition started");
      isRecording = true;
      voiceBtn.classList.add("recording");
      voiceBtn.innerText = "⏹️";
      voiceBtn.title = "Click to stop recording";
    };
    
    speechRecognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      console.log("Recognized text:", transcript);
      
      // Fill input field with recognized text
      userInput.value = transcript;
      userInput.focus();
      
      // Optional: Auto-send after recognition
      // Uncomment the next line if you want to auto-send
      // sendMessage(transcript);
    };
    
    speechRecognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      
      let errorMessage = "Speech recognition error: ";
      switch(event.error) {
        case 'no-speech':
          errorMessage = "No speech detected. Please try again.";
          break;
        case 'audio-capture':
          errorMessage = "No microphone found. Please check your microphone.";
          break;
        case 'not-allowed':
          errorMessage = "Microphone access denied. Please allow microphone access.";
          break;
        case 'network':
          errorMessage = "Network error. Please check your internet connection.";
          break;
        default:
          errorMessage = `Speech recognition error: ${event.error}`;
      }
      
      appendMessage(errorMessage, "bot");
    };
    
    speechRecognition.onend = () => {
      console.log("Speech recognition ended");
      isRecording = false;
      voiceBtn.classList.remove("recording");
      voiceBtn.innerText = "🎤";
      voiceBtn.title = "Click to start voice input";
    };
    
    console.log("✅ Browser speech recognition available");
  } else {
    console.log("❌ Browser speech recognition not available");
    // Fallback to our backend solution
    setupBackendVoiceRecognition();
  }
}

// Fallback: Setup backend voice recognition (if browser API not available)
function setupBackendVoiceRecognition() {
  console.log("Setting up backend voice recognition as fallback");
  
  voiceBtn.onclick = async () => {
    if (!isRecording) {
      await startRecording();
    } else {
      await stopRecordingAndProcess();
    }
  };
}

// Save all conversations (store in memory only)
function saveAll() {
  // Data persists only during session
  console.log("Conversations saved in memory");
}

// Get conversation context (last 7 exchanges with SQL queries)
function getConversationContext(conversationId) {
  if (!conversationId || !conversations[conversationId]) {
    return [];
  }
  
  const messages = conversations[conversationId].messages;
  const context = [];
  
  // Extract query-SQL pairs from messages
  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    if (msg.type === "user" && msg.sql) {
      context.push({
        query: msg.text,
        sql: msg.sql
      });
    }
  }
  
  // Return last 7 exchanges
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
  
  // Stop speech recognition if active
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
    
    // Render chart
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
    
    // Store SQL query with user messages for context
    if (type === "user" && sqlQuery) {
      messageData.sql = sqlQuery;
    }
    
    conversations[currentConversationId].messages.push(messageData);
    saveAll();
  }
}

// Show loading animation
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

// Remove loading animation
function hideLoading() {
  const loading = document.getElementById("loadingIndicator");
  if (loading) loading.remove();
}

// SEND MESSAGE
async function sendMessage(text) {
  if (!text || !text.trim()) return;

  // Ensure we have a conversation
  if (!currentConversationId) {
    const id = "conv_" + Date.now();
    conversations[id] = { messages: [] };
    currentConversationId = id;
    loadConversationList();
  }

  // Get conversation context (last 7 exchanges)
  const context = getConversationContext(currentConversationId);
  
  // Add user message (we'll update it with SQL after response)
  const userMessageIndex = conversations[currentConversationId].messages.length;
  appendMessage(text, "user", true, false, false, null, null);
  suggestionsBox.classList.add("hidden");

  showLoading();

  try {
    const res = await fetch("http://127.0.0.1:8000/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        query: text,
        conversation_id: currentConversationId,
        conversation_history: context
      })
    });

    const data = await res.json();
    hideLoading();

    // Update the user message with the SQL query for context
    if (data.sql && conversations[currentConversationId]) {
      conversations[currentConversationId].messages[userMessageIndex].sql = data.sql;
      saveAll();
    }

    // Handle errors
    if (data.result && data.result.error) {
      appendMessage(`Error: ${data.result.error}`, "bot");
      return;
    }

    // Check if backend wants to display a chart
    if (data.response_type === "chart" && data.chart) {
      appendMessage("", "bot", true, false, true, data.chart);
      return;
    }

    // Otherwise, render as table
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

// VOICE INPUT - Browser Speech Recognition (Primary)
voiceBtn.onclick = () => {
  if (speechRecognition) {
    // Use browser's built-in speech recognition
    if (!isRecording) {
      // Start speech recognition
      try {
        speechRecognition.start();
      } catch (error) {
        console.error("Error starting speech recognition:", error);
        appendMessage("Failed to start voice recognition. Please try again.", "bot");
      }
    } else {
      // Stop speech recognition
      speechRecognition.stop();
    }
  } else {
    // Fallback to backend solution
    if (!isRecording) {
      startRecordingBackend();
    } else {
      stopRecordingBackend();
    }
  }
};

// BACKEND FALLBACK FUNCTIONS (if browser API not available)
async function startRecordingBackend() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (e) => {
      audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.wav');

      // Show processing indicator
      voiceBtn.innerText = "⏳";
      voiceBtn.disabled = true;

      try {
        const res = await fetch("http://127.0.0.1:8000/voice", {
          method: "POST",
          body: formData
        });

        const data = await res.json();

        if (data.success && data.text) {
          // Fill input field with recognized text
          userInput.value = data.text;
          userInput.focus();
          
          // Show a brief success indicator
          voiceBtn.innerText = "✓";
          setTimeout(() => {
            voiceBtn.innerText = "🎤";
          }, 1000);
        } else {
          // Show error message
          const errorMsg = data.error || "Could not recognize speech";
          appendMessage(errorMsg, "bot");
          voiceBtn.innerText = "🎤";
        }
      } catch (error) {
        console.error("Voice processing error:", error);
        appendMessage("Voice processing error. Please try again.", "bot");
        voiceBtn.innerText = "🎤";
      } finally {
        voiceBtn.disabled = false;
      }

      stream.getTracks().forEach(track => track.stop());
    };

    mediaRecorder.start();
    isRecording = true;
    voiceBtn.classList.add("recording");
    voiceBtn.innerText = "⏹️";
  } catch (error) {
    console.error("Microphone error:", error);
    appendMessage("Microphone access denied. Please allow microphone access.", "bot");
  }
}

function stopRecordingBackend() {
  if (mediaRecorder) {
    mediaRecorder.stop();
    isRecording = false;
    voiceBtn.classList.remove("recording");
    voiceBtn.innerText = "🎤";
  }
}

// Suggestion button click
document.querySelectorAll(".suggest-btn").forEach(btn => {
  btn.onclick = () => {
    userInput.value = btn.innerText;
    document.getElementById("sendBtn").click();
  };
});

// Enter key to send
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

// Add keyboard shortcut for voice input (Ctrl+Space)
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === ' ' && !e.repeat) {
    e.preventDefault();
    voiceBtn.click();
  }
});
