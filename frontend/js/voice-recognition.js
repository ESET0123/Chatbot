// Voice Recognition Module

class VoiceRecognition {
  constructor() {
    this.isRecording = false;
    this.recognition = null;
    this.voiceBtn = document.getElementById("voiceBtn");
    this.userInput = document.getElementById("userInput");
    this.onTranscriptCallback = null;
    this.onErrorCallback = null;

    this.init();
  }

  init() {
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.lang = "en-US";

      this.recognition.onstart = () => {
        this.isRecording = true;
        this.voiceBtn.classList.add("recording");
        this.voiceBtn.innerText = "⏹️";
      };

      this.recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        this.userInput.value = transcript;
        
        if (this.onTranscriptCallback) {
          this.onTranscriptCallback(transcript);
        }
      };

      this.recognition.onerror = (error) => {
        console.error("Speech recognition error:", error);
        
        if (this.onErrorCallback) {
          this.onErrorCallback(error);
        }
      };

      this.recognition.onend = () => {
        this.isRecording = false;
        this.voiceBtn.classList.remove("recording");
        this.voiceBtn.innerText = "🎤";
      };
    }
  }

  isAvailable() {
    return this.recognition !== null;
  }

  toggle() {
    if (!this.isAvailable()) {
      console.warn("Speech recognition not available");
      return;
    }

    if (this.isRecording) {
      this.stop();
    } else {
      this.start();
    }
  }

  start() {
    if (this.recognition && !this.isRecording) {
      this.recognition.start();
    }
  }

  stop() {
    if (this.recognition && this.isRecording) {
      this.recognition.stop();
    }
  }

  onTranscript(callback) {
    this.onTranscriptCallback = callback;
  }

  onError(callback) {
    this.onErrorCallback = callback;
  }
}

export default new VoiceRecognition();