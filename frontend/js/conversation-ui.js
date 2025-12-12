// Conversation UI Manager Module - Fixed for persistence

class ConversationUI {
  constructor() {
    this.conversations = {}; // { conversationId: { title, created_at, last_updated, messages: [] } }
    this.currentConversationId = null;
    this.messagesContainer = document.getElementById("messages");
    this.suggestionsBox = document.getElementById("suggestionsBox");
    this.conversationList = document.getElementById("conversationList");
    this.apiService = null; // Will be set from app.js
  }

  setApiService(apiService) {
    this.apiService = apiService;
  }

  async loadConversationsFromServer() {
    if (!this.apiService) {
      console.error("API service not set");
      return;
    }

    try {
      console.log("📥 Loading conversations from server...");
      const response = await this.apiService.listConversations();
      const serverConversations = response.conversations || [];
      
      console.log(`Found ${serverConversations.length} conversations`);
      
      // Clear existing conversations
      this.conversations = {};
      
      // Load each conversation metadata
      serverConversations.forEach(conv => {
        this.conversations[conv.conversation_id] = {
          title: conv.title || "New Chat",
          created_at: conv.created_at,
          last_updated: conv.last_updated,
          messages: [], // Will be loaded on demand
          loaded: false // Track if messages have been loaded
        };
      });
      
      this.renderConversationList();
      
      // If there are conversations, load the most recent one
      if (serverConversations.length > 0) {
        const mostRecent = serverConversations[0];
        await this.loadConversation(mostRecent.conversation_id);
      } else {
        // No conversations, show suggestions
        this.showSuggestions();
      }
      
    } catch (error) {
      console.error("Failed to load conversations:", error);
    }
  }

  async loadConversation(conversationId) {
    if (!this.apiService) return;

    try {
      console.log(`📖 Loading conversation: ${conversationId}`);
      
      this.currentConversationId = conversationId;
      this.clearMessages();
      
      // Fetch messages from backend
      const response = await this.apiService.getConversationMessages(conversationId);
      const messages = response.messages || [];
      
      console.log(`Loaded ${messages.length} messages`);
      
      // Store messages locally
      if (!this.conversations[conversationId]) {
        this.conversations[conversationId] = {
          title: "Chat",
          messages: [],
          loaded: true
        };
      }
      
      this.conversations[conversationId].messages = [];
      
      // Render each message
      for (const msg of messages) {
        if (msg.type === "user") {
          this.appendMessage(msg.content, "user", false, false, false, null, msg.sql);
        } else if (msg.type === "bot") {
          if (msg.error) {
            this.appendMessage(`Error: ${msg.error}`, "bot", false);
          } else if (msg.result) {
            // Check if it should be a chart
            const hasChartData = msg.result.rows && msg.result.rows.length > 0 && 
                                msg.result.columns && msg.result.columns.length >= 2;
            
            if (hasChartData) {
              // For now, render as table. Chart logic can be added if needed.
              const tableHTML = this.renderTableResult(msg.result);
              this.appendMessage(tableHTML, "bot", false, true);
            } else {
              const tableHTML = this.renderTableResult(msg.result);
              this.appendMessage(tableHTML, "bot", false, true);
            }
          }
        }
      }
      
      this.conversations[conversationId].loaded = true;
      
      if (messages.length > 0) {
        this.hideSuggestions();
      } else {
        this.showSuggestions();
      }
      
      this.renderConversationList();
      
    } catch (error) {
      console.error("Failed to load conversation:", error);
      this.appendMessage("Failed to load conversation history.", "bot");
    }
  }

  createNewConversation() {
    const id = "conv_" + Date.now();
    
    this.conversations[id] = { 
      title: "New Chat",
      created_at: new Date().toISOString(),
      last_updated: new Date().toISOString(),
      messages: [],
      loaded: true
    };
    
    this.currentConversationId = id;
    this.clearMessages();
    this.showSuggestions();
    this.renderConversationList();
    
    console.log(`✨ Created new conversation: ${id}`);
    return id;
  }

  getCurrentConversationId() {
    return this.currentConversationId;
  }

  getConversationContext(conversationId) {
    if (!conversationId || !this.conversations[conversationId]) {
      return [];
    }

    const msgs = this.conversations[conversationId].messages;
    const context = [];

    msgs.forEach((msg) => {
      if (msg.type === "user" && msg.sql) {
        context.push({ query: msg.text, sql: msg.sql });
      }
    });

    return context.slice(-7);
  }

  appendMessage(content, type, save = true, isHTML = false, isChart = false, chartConfig = null, sqlQuery = null) {
    const msg = document.createElement("div");
    msg.classList.add("message", type);

    if (isChart && chartConfig) {
      const chartDiv = document.createElement("div");
      const canvas = document.createElement("canvas");
      chartDiv.appendChild(canvas);
      msg.appendChild(chartDiv);
      new Chart(canvas, chartConfig);
    } else if (isHTML) {
      msg.innerHTML = content;
    } else {
      msg.innerText = content;
    }

    this.messagesContainer.appendChild(msg);
    this.scrollToBottom();

    if (save && this.currentConversationId) {
      const entry = {
        text: content,
        type,
        isHTML,
        isChart,
        chartConfig: isChart ? chartConfig : null,
      };
      
      if (type === "user" && sqlQuery) {
        entry.sql = sqlQuery;
      }
      
      if (!this.conversations[this.currentConversationId]) {
        this.conversations[this.currentConversationId] = { 
          messages: [],
          title: "New Chat"
        };
      }
      
      this.conversations[this.currentConversationId].messages.push(entry);
      
      // Update title if this is the first user message
      const msgs = this.conversations[this.currentConversationId].messages;
      const userMessages = msgs.filter(m => m.type === "user");
      
      if (type === "user" && userMessages.length === 1) {
        const title = content.length > 50 ? content.slice(0, 50) + "..." : content;
        this.conversations[this.currentConversationId].title = title;
        this.conversations[this.currentConversationId].last_updated = new Date().toISOString();
        this.renderConversationList();
      }
    }
  }

  updateLastUserMessageSQL(sql) {
    if (!this.currentConversationId) return;
    
    const conv = this.conversations[this.currentConversationId];
    if (!conv || !conv.messages) return;
    
    const messages = conv.messages;
    
    // Find the last user message
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].type === "user") {
        messages[i].sql = sql;
        break;
      }
    }
  }

  clearMessages() {
    this.messagesContainer.innerHTML = "";
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  showSuggestions() {
    this.suggestionsBox.classList.remove("hidden");
  }

  hideSuggestions() {
    this.suggestionsBox.classList.add("hidden");
  }

  showLoading() {
    const div = document.createElement("div");
    div.id = "loadingIndicator";
    div.className = "loading";
    div.innerHTML = `
      <div class="loading-dot"></div>
      <div class="loading-dot"></div>
      <div class="loading-dot"></div>
    `;
    this.messagesContainer.appendChild(div);
    this.scrollToBottom();
  }

  hideLoading() {
    const loader = document.getElementById("loadingIndicator");
    if (loader) loader.remove();
  }

  renderConversationList() {
    this.conversationList.innerHTML = "";

    // Sort conversations by last_updated (most recent first)
    const sortedConvs = Object.entries(this.conversations)
      .sort((a, b) => {
        const dateA = new Date(a[1].last_updated || a[1].created_at || 0);
        const dateB = new Date(b[1].last_updated || b[1].created_at || 0);
        return dateB - dateA;
      });

    sortedConvs.forEach(([id, conv]) => {
      const div = document.createElement("div");
      div.className = "conversation-item";
      
      if (id === this.currentConversationId) {
        div.classList.add("active");
      }
      
      const title = conv.title || "New Chat";
      const preview = title.length > 35 ? title.slice(0, 35) + "..." : title;
      
      div.innerHTML = `
        <div class="conv-title">${preview}</div>
        <div class="conv-date">${this.formatDate(conv.last_updated || conv.created_at)}</div>
      `;
      
      div.onclick = () => this.loadConversation(id);
      this.conversationList.appendChild(div);
    });
  }

  formatDate(dateString) {
    if (!dateString) return "";
    
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
  }

  renderTableResult(result) {
    if (!result.rows || result.rows.length === 0) {
      return "No data found.";
    }

    return `
      <div class="table-info">
        <small>${result.rows.length} rows returned</small>
      </div>
      <div class="overflow-auto">
        <table>
          <thead>
            <tr>
              ${result.columns.map((c) => `<th>${c}</th>`).join("")}
            </tr>
          </thead>
          <tbody>
            ${result.rows
              .map(
                (row) =>
                  `<tr>${row
                    .map((cell) => `<td>${cell !== null ? cell : ""}</td>`)
                    .join("")}</tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }
}

export default new ConversationUI();