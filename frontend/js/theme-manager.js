// Theme Manager Module

class ThemeManager {
  constructor() {
    this.themeBtn = document.getElementById("themeToggle");
    this.currentTheme = this.loadTheme();
    this.applyTheme(this.currentTheme);
  }

  loadTheme() {
    const saved = localStorage.getItem("theme");
    return saved || "light";
  }

  saveTheme(theme) {
    localStorage.setItem("theme", theme);
  }

  applyTheme(theme) {
    document.body.classList.remove("light", "dark");
    document.body.classList.add(theme);
    
    this.themeBtn.innerText = theme === "dark" ? "☀️" : "🌙";
    this.currentTheme = theme;
    this.saveTheme(theme);
  }

  toggle() {
    const newTheme = this.currentTheme === "light" ? "dark" : "light";
    this.applyTheme(newTheme);
  }

  getCurrentTheme() {
    return this.currentTheme;
  }
}

export default new ThemeManager();