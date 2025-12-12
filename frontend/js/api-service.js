// API Service Module - Handles all backend communication

const API_URL = "http://127.0.0.1:8000";

class ApiService {
  constructor() {
    this.token = null;
  }

  setToken(token) {
    this.token = token;
  }

  getHeaders() {
    const headers = {
      "Content-Type": "application/json",
    };
    
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    
    return headers;
  }

  async verifyAuth() {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: this.getHeaders(),
    });

    if (!res.ok) {
      throw new Error("Invalid token");
    }

    return await res.json();
  }

  async login(email, password) {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Login failed");
    }

    return data;
  }

  async register(email, password) {
    const res = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Registration failed");
    }

    return data;
  }

  async sendQuery(query, conversationId, conversationHistory) {
    const res = await fetch(`${API_URL}/ask`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        query,
        conversation_id: conversationId,
        conversation_history: conversationHistory,
      }),
    });

    if (res.status === 401) {
      throw new Error("Session expired");
    }

    if (!res.ok) {
      throw new Error("Query failed");
    }

    return await res.json();
  }

  async listConversations() {
    const res = await fetch(`${API_URL}/conversations`, {
      headers: this.getHeaders(),
    });

    if (!res.ok) {
      throw new Error("Failed to fetch conversations");
    }

    return await res.json();
  }

  async getConversationMessages(conversationId) {
    const res = await fetch(`${API_URL}/conversations/${conversationId}/messages`, {
      headers: this.getHeaders(),
    });

    if (!res.ok) {
      throw new Error("Failed to fetch conversation messages");
    }

    return await res.json();
  }

  async getContext(conversationId) {
    const res = await fetch(`${API_URL}/context/${conversationId}`, {
      headers: this.getHeaders(),
    });

    if (!res.ok) {
      throw new Error("Failed to fetch context");
    }

    return await res.json();
  }

  async clearContext(conversationId) {
    const res = await fetch(`${API_URL}/context/${conversationId}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });

    if (!res.ok) {
      throw new Error("Failed to clear context");
    }

    return await res.json();
  }
}

export default new ApiService();