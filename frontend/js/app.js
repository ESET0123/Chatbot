// Main Application Controller

import apiService from './api-service.js';
import authManager from './auth-manager.js';
import conversationUI from './conversation-ui.js';
import voiceRecognition from './voice-recognition.js';
import themeManager from './theme-manager.js';

class App {
  constructor() {
    this.isProcessingMessage = false;
    this.userInput = document.getElementById("userInput");
    this.sendBtn = document.getElementById("sendBtn");
    
    this.init();
  }

  async init() {
    console.log("🚀 Application initializing...");

    // Check authentication
    const user = await authManager.checkAuth();
    if (!user) return;

    // Set API service reference in conversationUI
    conversationUI.setApiService(apiService);

    this.displayUserInfo(user);
    
    // Load conversations from server (this will also load the most recent one)
    await conversationUI.loadConversationsFromServer();
    
    this.setupEventListeners();
    this.preventFormSubmission();

    console.log("✅ Application ready");
  }

  displayUserInfo(user) {
    const currentUser = authManager.getCurrentUser();
    document.getElementById("nameDisplay").textContent = currentUser.name || "User";
    document.getElementById("emailDisplay").textContent = currentUser.email;
    this.updateUserAvatar(currentUser.name);
  }

  updateUserAvatar(name) {
    const avatarElement = document.getElementById("userAvatar");
    if (avatarElement && name) {
        // Get first letter of first name
        const initial = name.trim().charAt(0).toUpperCase();
        avatarElement.textContent = initial;
    }
    }

  setupEventListeners() {
    // New chat button
    document.getElementById("newChatBtn").onclick = () => {
      conversationUI.createNewConversation();
    };

    // Send button
    this.sendBtn.onclick = () => this.handleSendMessage();

    // Enter key
    this.userInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        this.handleSendMessage();
      }
    });

    // Voice button
    document.getElementById("voiceBtn").onclick = () => {
      voiceRecognition.toggle();
    };

    // Theme toggle
    document.getElementById("themeToggle").onclick = () => {
      themeManager.toggle();
    };

    // Sidebar toggle
    document.getElementById("toggleSidebar").onclick = () => {
  const sidebar = document.getElementById("sidebar");
  const toggleBtn = document.getElementById("toggleSidebar");

  sidebar.classList.toggle("collapsed");

  // Update button direction
  if (!sidebar.classList.contains("collapsed")) {
    toggleBtn.textContent = "<>";   // Sidebar collapsed → show expand arrows
  } else {
    toggleBtn.textContent = ">>";   // Sidebar open → show collapse arrows
  }
};


    // Logout
    document.getElementById("logoutBtn").onclick = (e) => {
      e.preventDefault();
      authManager.logout();
    };

    // Suggestion buttons
    document.querySelectorAll(".suggest-btn").forEach((btn) => {
      btn.onclick = () => {
        this.userInput.value = btn.innerText;
        this.handleSendMessage();
      };
    });

    // Voice shortcuts
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === " ") {
        e.preventDefault();
        voiceRecognition.toggle();
      }
    });
  }

  preventFormSubmission() {
    document.addEventListener(
      "submit",
      (e) => {
        e.preventDefault();
        e.stopPropagation();
      },
      true
    );

    window.addEventListener("beforeunload", (e) => {
      if (this.isProcessingMessage) {
        e.preventDefault();
        e.returnValue = "";
      }
    });
  }

  async handleSendMessage() {
    const text = this.userInput.value.trim();
    
    if (!text) return;
    if (this.isProcessingMessage) {
      console.warn("⚠️ Already processing message");
      return;
    }

    this.isProcessingMessage = true;
    this.userInput.value = "";

    // Ensure conversation exists
    let conversationId = conversationUI.getCurrentConversationId();
    if (!conversationId) {
      conversationId = conversationUI.createNewConversation();
    }

    const context = conversationUI.getConversationContext(conversationId);

    // Display user message
    conversationUI.appendMessage(text, "user");
    conversationUI.hideSuggestions();
    conversationUI.showLoading();

    try {
      const data = await apiService.sendQuery(text, conversationId, context);
      conversationUI.hideLoading();

      // Save SQL to last user message
      if (data.sql) {
        conversationUI.updateLastUserMessageSQL(data.sql);
      }

      // Handle errors
      if (data.result && data.result.error) {
        conversationUI.appendMessage(`Error: ${data.result.error}`, "bot");
        return;
      }

      // Handle chart response
      if (data.response_type === "chart") {
        conversationUI.appendMessage("", "bot", true, false, true, data.chart);
        return;
      }

      // Handle table response
      const tableHTML = conversationUI.renderTableResult(data.result);
      conversationUI.appendMessage(tableHTML, "bot", true, true);

    } catch (error) {
      console.error("💥 Error:", error);
      conversationUI.hideLoading();

      if (error.message === "Session expired") {
        conversationUI.appendMessage("Session expired. Redirecting to login...", "bot");
        setTimeout(() => authManager.logout(), 2000);
      } else {
        conversationUI.appendMessage(
          "Connection error. Please check if the server is running.",
          "bot"
        );
      }
    } finally {
      this.isProcessingMessage = false;
    }
  }
}

// Initialize app when DOM is ready
window.addEventListener("DOMContentLoaded", () => {
  new App();
});