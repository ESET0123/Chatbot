// // GLOBALS
// let conversations = {};
// let currentConversationId = null;
// let isRecording = false;
// let mediaRecorder = null;
// let audioChunks = [];
// let authToken = null;
// let currentUser = null;
// let isProcessingMessage = false;

// const messagesContainer = document.getElementById("messages");
// const suggestionsBox = document.getElementById("suggestionsBox");
// const voiceBtn = document.getElementById("voiceBtn");
// const userInput = document.getElementById("userInput");
// const API_URL = "http://127.0.0.1:8000";

// let speechRecognition = null;

// // FAST DEBUG LOGGER (no delays)
// function debugLog(message, data = null) {
//   console.log(`[DEBUG] ${message}`, data || "");
// }

// // PREVENT NAVIGATION DURING MESSAGE PROCESSING
// window.addEventListener("beforeunload", (e) => {
//   if (isProcessingMessage) {
//     debugLog("⚠️ BEFOREUNLOAD EVENT - Message processing in progress!");
//   }
// });

// // Prevent all forms from submitting
// document.addEventListener(
//   "submit",
//   (e) => {
//     debugLog("⚠️ FORM SUBMIT EVENT CAUGHT AND PREVENTED!");
//     e.preventDefault();
//     e.stopPropagation();
//   },
//   true
// );

// // On load
// window.onload = async () => {
//   debugLog("🚀 Page loaded, starting authentication check");
//   await checkAuth();
//   debugLog("✅ Auth check complete");
//   loadConversationList();
//   initBrowserSpeechRecognition();
// };

// // ------------ AUTH CHECK ------------
// async function checkAuth() {
//   debugLog("🔐 Starting checkAuth()");
//   authToken = sessionStorage.getItem("token");
//   const userJson = sessionStorage.getItem("user");

//   debugLog("Token from storage:", authToken);
//   debugLog("User from storage:", userJson);

//   if (!authToken || !userJson) {
//     debugLog("❌ No token or user found, redirecting to login");
//     window.location.href = "./../backend/auth.html";
//     return;
//   }

//   currentUser = JSON.parse(userJson);
//   debugLog("👤 Current user parsed:", currentUser);

//   try {
//     debugLog("🌐 Verifying token with /auth/me");
//     const res = await fetch(`${API_URL}/auth/me`, {
//       headers: {
//         Authorization: `Bearer ${authToken}`,
//       },
//     });

//     debugLog("Response status:", res.status);

//     if (!res.ok) throw new Error("Invalid token");

//     const userData = await res.json();
//     debugLog("✅ Token verified, user data:", userData);

//     document.getElementById("nameDisplay").textContent = currentUser.name;
//     document.getElementById("emailDisplay").textContent = currentUser.email;
//   } catch (error) {
//     debugLog("❌ Auth verification failed:", error);
//     sessionStorage.removeItem("token");
//     sessionStorage.removeItem("user");
//     window.location.href = "./../backend/auth.html";
//   }
// }

// // ------------ LOGOUT ------------
// document.getElementById("logoutBtn").addEventListener("click", (e) => {
//   e.preventDefault();
//   debugLog("🚪 Logout clicked");
//   sessionStorage.removeItem("token");
//   sessionStorage.removeItem("user");
//   window.location.href = "./../backend/auth.html";
// });

// // ------------ SPEECH RECOGNITION ------------
// function initBrowserSpeechRecognition() {
//   debugLog("🎤 Initializing speech recognition");
//   if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
//     const SpeechRecognition =
//       window.SpeechRecognition || window.webkitSpeechRecognition;
//     speechRecognition = new SpeechRecognition();

//     speechRecognition.continuous = false;
//     speechRecognition.interimResults = false;
//     speechRecognition.lang = "en-US";

//     speechRecognition.onstart = () => {
//       isRecording = true;
//       voiceBtn.classList.add("recording");
//       voiceBtn.innerText = "⏹️";
//     };

//     speechRecognition.onresult = (event) => {
//       const transcript = event.results[0][0].transcript;
//       userInput.value = transcript;
//     };

//     speechRecognition.onerror = () => {
//       appendMessage("Speech error", "bot");
//     };

//     speechRecognition.onend = () => {
//       isRecording = false;
//       voiceBtn.classList.remove("recording");
//       voiceBtn.innerText = "🎤";
//     };
//   }
// }

// function saveAll() {
//   console.log("Conversations saved in memory");
// }

// // ------------ CONTEXT LOGIC ------------
// function getConversationContext(conversationId) {
//   if (!conversationId || !conversations[conversationId]) return [];

//   const msgs = conversations[conversationId].messages;
//   const context = [];

//   msgs.forEach((msg) => {
//     if (msg.type === "user" && msg.sql) {
//       context.push({ query: msg.text, sql: msg.sql });
//     }
//   });

//   return context.slice(-7);
// }

// // ------------ NEW CHAT ------------
// document.getElementById("newChatBtn").onclick = () => {
//   debugLog("➕ New chat clicked");
//   const id = "conv_" + Date.now();
//   conversations[id] = { messages: [] };
//   currentConversationId = id;
//   saveAll();
//   loadConversationList();
//   messagesContainer.innerHTML = "";
//   suggestionsBox.classList.remove("hidden");
// };

// // ------------ LOAD CONVERSATION LIST ------------
// function loadConversationList() {
//   const list = document.getElementById("conversationList");
//   list.innerHTML = "";

//   Object.keys(conversations).forEach((id) => {
//     const div = document.createElement("div");
//     div.className = "conversation-item";
//     const firstMsg = conversations[id].messages.find((m) => m.type === "user");
//     div.innerText = firstMsg ? firstMsg.text.slice(0, 30) : "New Chat";
//     div.onclick = () => loadConversation(id);
//     list.appendChild(div);
//   });
// }

// // ------------ LOAD CONVERSATION ------------
// function loadConversation(id) {
//   debugLog("📂 Loading conversation:", id);
//   currentConversationId = id;
//   messagesContainer.innerHTML = "";

//   const msgs = conversations[id].messages;

//   msgs.forEach((m) => {
//     if (m.isChart) {
//       appendMessage("", m.type, false, false, true, m.chartConfig);
//     } else if (m.isHTML) {
//       appendMessage(m.text, m.type, false, true);
//     } else {
//       appendMessage(m.text, m.type);
//     }
//   });

//   const hasUserMsg = msgs.some((m) => m.type === "user");
//   suggestionsBox.classList.toggle("hidden", hasUserMsg);
// }

// // ------------ APPEND MESSAGE ------------
// function appendMessage(
//   content,
//   type,
//   save = true,
//   isHTML = false,
//   isChart = false,
//   chartConfig = null,
//   sqlQuery = null
// ) {
//   const msg = document.createElement("div");
//   msg.classList.add("message", type);

//   if (isChart && chartConfig) {
//     const chartDiv = document.createElement("div");
//     const canvas = document.createElement("canvas");
//     chartDiv.appendChild(canvas);
//     msg.appendChild(chartDiv);
//     new Chart(canvas, chartConfig);
//   } else if (isHTML) {
//     msg.innerHTML = content;
//   } else {
//     msg.innerText = content;
//   }

//   messagesContainer.appendChild(msg);
//   messagesContainer.scrollTop = messagesContainer.scrollHeight;

//   if (save && currentConversationId) {
//     const entry = {
//       text: content,
//       type,
//       isHTML,
//       isChart,
//       chartConfig: isChart ? chartConfig : null,
//     };
//     if (type === "user" && sqlQuery) entry.sql = sqlQuery;
//     conversations[currentConversationId].messages.push(entry);
//     saveAll();
//   }
// }

// // ------------ LOADING SPINNER ------------
// function showLoading() {
//   const div = document.createElement("div");
//   div.id = "loadingIndicator";
//   div.className = "loading";
//   div.innerHTML = `
//       <div class="loading-dot"></div>
//       <div class="loading-dot"></div>
//       <div class="loading-dot"></div>
//   `;
//   messagesContainer.appendChild(div);
// }
// function hideLoading() {
//   const l = document.getElementById("loadingIndicator");
//   if (l) l.remove();
// }

// // ------------ SEND MESSAGE ------------
// async function sendMessage(text) {
//   debugLog("📤 sendMessage:", text);

//   if (!text.trim()) return;
//   if (isProcessingMessage) return debugLog("⚠️ Already processing message");

//   isProcessingMessage = true;

//   if (!currentConversationId) {
//     const id = "conv_" + Date.now();
//     conversations[id] = { messages: [] };
//     currentConversationId = id;
//     loadConversationList();
//   }

//   const context = getConversationContext(currentConversationId);

//   appendMessage(text, "user");
//   suggestionsBox.classList.add("hidden");
//   showLoading();

//   try {
//     const res = await fetch(`${API_URL}/ask`, {
//       method: "POST",
//       headers: {
//         "Content-Type": "application/json",
//         Authorization: `Bearer ${authToken}`,
//       },
//       body: JSON.stringify({
//         query: text,
//         conversation_id: currentConversationId,
//         conversation_history: context,
//       }),
//     });

//     debugLog("📥 Response status:", res.status);

//     if (res.status === 401) {
//       hideLoading();
//       appendMessage("Session expired. Please login again.", "bot");
//       sessionStorage.clear();
//       window.location.href = "./../backend/auth.html";
//       return;
//     }

//     const data = await res.json();
//     hideLoading();
//     debugLog("📦 Response:", data);

//     if (data.sql) {
//       const idx = conversations[currentConversationId].messages.length - 1;
//       conversations[currentConversationId].messages[idx].sql = data.sql;
//       saveAll();
//     }

//     if (data.result && data.result.error) {
//       appendMessage(`Error: ${data.result.error}`, "bot");
//       return;
//     }

//     if (data.response_type === "chart") {
//       appendMessage("", "bot", true, false, true, data.chart);
//       return;
//     }

//     if (!data.result.rows || data.result.rows.length === 0) {
//       appendMessage("No data found.", "bot");
//       return;
//     }

//     let tableHTML = `
//       <div class="table-info">
//         <small>${data.result.rows.length} rows returned</small>
//       </div>
//       <div class="overflow-auto">
//         <table>
//           <thead>
//             <tr>
//               ${data.result.columns.map((c) => `<th>${c}</th>`).join("")}
//             </tr>
//           </thead>
//           <tbody>
//             ${data.result.rows
//               .map(
//                 (row) =>
//                   `<tr>${row
//                     .map((cell) => `<td>${cell !== null ? cell : ""}</td>`)
//                     .join("")}</tr>`
//               )
//               .join("")}
//           </tbody>
//         </table>
//       </div>
//     `;

//     appendMessage(tableHTML, "bot", true, true);
//   } catch (err) {
//     debugLog("💥 FETCH ERROR:", err);
//     hideLoading();
//     appendMessage(
//       "Connection error. Please check if the server is running.",
//       "bot"
//     );
//   } finally {
//     isProcessingMessage = false;
//   }
// }

// // ------------ BUTTON HANDLERS ------------
// document.getElementById("sendBtn").onclick = () => {
//   debugLog("🖱️ Send click");
//   const text = userInput.value.trim();
//   userInput.value = "";
//   sendMessage(text);
// };

// voiceBtn.onclick = () => {
//   if (speechRecognition) {
//     if (!isRecording) speechRecognition.start();
//     else speechRecognition.stop();
//   }
// };

// document.querySelectorAll(".suggest-btn").forEach((btn) => {
//   btn.onclick = () => {
//     userInput.value = btn.innerText;
//     document.getElementById("sendBtn").click();
//   };
// });

// userInput.addEventListener("keypress", (e) => {
//   if (e.key === "Enter") {
//     e.preventDefault();
//     document.getElementById("sendBtn").click();
//   }
// });

// // Sidebar toggle
// document.getElementById("toggleSidebar").onclick = () => {
//   document.getElementById("sidebar").classList.toggle("collapsed");
// };

// // Theme toggle
// document.getElementById("themeToggle").onclick = () => {
//   const body = document.body;
//   const btn = document.getElementById("themeToggle");

//   if (body.classList.contains("dark")) {
//     body.classList.replace("dark", "light");
//     btn.innerText = "☀️";
//   } else {
//     body.classList.replace("light", "dark");
//     btn.innerText = "🌙";
//   }
// };

// // Voice shortcut
// document.addEventListener("keydown", (e) => {
//   if ((e.ctrlKey || e.metaKey) && e.key === " ") {
//     e.preventDefault();
//     voiceBtn.click();
//   }
// });
