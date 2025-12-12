// Authentication Manager Module

import apiService from './api-service.js';

class AuthManager {
  constructor() {
    this.currentUser = null;
  }

  async checkAuth() {
    const token = sessionStorage.getItem("token");
    const userJson = sessionStorage.getItem("user");

    if (!token || !userJson) {
      this.redirectToLogin();
      return null;
    }

    this.currentUser = JSON.parse(userJson);
    apiService.setToken(token);

    try {
      const userData = await apiService.verifyAuth();
      return userData;
    } catch (error) {
      console.error("Auth verification failed:", error);
      this.logout();
      return null;
    }
  }

  saveAuthData(token, userId, email, name = "User") {
    sessionStorage.setItem("token", token);
    sessionStorage.setItem("user", JSON.stringify({
      id: userId,
      name: name,
      email: email
    }));

    this.currentUser = { id: userId, name, email };
    apiService.setToken(token);
  }

  logout() {
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("user");
    this.currentUser = null;
    this.redirectToLogin();
  }

  redirectToLogin() {
    window.location.href = "../backend/auth.html";
  }

  getCurrentUser() {
    return this.currentUser;
  }

  isAuthenticated() {
    return !!sessionStorage.getItem("token");
  }
}

export default new AuthManager();