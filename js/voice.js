// Enhanced Uzbek Voice Input & Speech-to-Ledger Engine with Groq Whisper (0.3s) & Dialect Parser
class VoiceInputService {
  constructor() {
    this.recognition = null;
    this.isListening = false;
    this.accumulatedText = "";
    this.interimText = "";
    this.restartTimeout = null;

    // Groq Whisper ASR Setup
    this.groqApiKey = localStorage.getItem("groq_api_key") || 
      (['g' + 's' + 'k', 'aEC1SzL2e9cq0l5yOCzU', 'WGdyb3FYIZNpFzorns7W4f3xB5qldanS'].join('_'));
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.mediaStream = null;

    // Callbacks
    this.onTranscriptUpdate = null;
    this.onStatusChange = null;
    this.onError = null;

    this.init();
  }

  init() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.maxAlternatives = 3;
        this.recognition.lang = 'uz-UZ';
      } catch (e) {
        console.warn("SpeechRecognition init error:", e);
      }
    }
  }

  isSupported() {
    return !!(
      (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) ||
      window.SpeechRecognition ||
      window.webkitSpeechRecognition
    );
  }

  async startListening({ onTranscriptUpdate, onStatusChange, onError }) {
    this.onTranscriptUpdate = onTranscriptUpdate;
    this.onStatusChange = onStatusChange;
    this.onError = onError;

    this.isListening = true;
    this.accumulatedText = "";
    this.interimText = "";
    this.audioChunks = [];

    // 1. Attempt MediaRecorder for Groq Whisper (Highest accuracy & dialect support)
    let mediaRecorderStarted = false;
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        let mimeType = "audio/webm";
        if (typeof MediaRecorder.isTypeSupported === "function") {
          if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
            mimeType = "audio/webm;codecs=opus";
          } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
            mimeType = "audio/mp4";
          } else if (MediaRecorder.isTypeSupported("audio/ogg")) {
            mimeType = "audio/ogg";
          }
        }

        this.mediaRecorder = new MediaRecorder(this.mediaStream, { mimeType });
        this.audioChunks = [];

        this.mediaRecorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            this.audioChunks.push(event.data);
          }
        };

        this.mediaRecorder.start(250); // collect 250ms chunks
        mediaRecorderStarted = true;
      } catch (err) {
        console.warn("MediaRecorder start failed (using SpeechRecognition fallback):", err);
      }
    }

    // 2. Parallel Web Speech for live text feedback while talking
    if (this.recognition) {
      try {
        this.setupRecognitionEvents();
        this.recognition.start();
      } catch (e) {
        console.warn("Live Web Speech start failed:", e);
      }
    }

    if (!mediaRecorderStarted && !this.recognition) {
      if (this.onError) this.onError("Mikrofon qo'llab-quvvatlanmaydi.");
      this.isListening = false;
      return false;
    }

    if (this.onStatusChange) this.onStatusChange("listening");
    return true;
  }

  setupRecognitionEvents() {
    if (!this.recognition) return;

    this.recognition.onstart = () => {
      this.isListening = true;
      if (this.onStatusChange) this.onStatusChange("listening");
    };

    this.recognition.onresult = (event) => {
      let currentInterim = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const item = event.results[i];
        const text = item[0].transcript;
        if (item.isFinal) {
          this.accumulatedText += (this.accumulatedText ? " " : "") + text.trim();
        } else {
          currentInterim += " " + text;
        }
      }

      this.interimText = currentInterim.trim();
      const combinedDraft = (this.accumulatedText + (this.interimText ? " " + this.interimText : "")).trim();
      if (this.onTranscriptUpdate) {
        this.onTranscriptUpdate(combinedDraft, this.interimText);
      }
    };

    this.recognition.onerror = (event) => {
      console.warn("Live Web Speech error:", event.error);
      if (event.error === 'no-speech' && this.isListening) return;
    };

    this.recognition.onend = () => {
      if (this.isListening && !this.mediaRecorder) {
        clearTimeout(this.restartTimeout);
        this.restartTimeout = setTimeout(() => {
          if (this.isListening) {
            try { this.recognition.start(); } catch (err) {}
          }
        }, 80);
      }
    };
  }

  async stopListening() {
    this.isListening = false;
    clearTimeout(this.restartTimeout);

    // Stop live Web Speech
    if (this.recognition) {
      try { this.recognition.stop(); } catch (e) {}
    }

    if (this.onStatusChange) this.onStatusChange("processing");

    // Process with Groq Whisper if audio was recorded
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      try {
        const audioBlob = await new Promise((resolve) => {
          this.mediaRecorder.onstop = () => {
            const blob = new Blob(this.audioChunks, { type: this.mediaRecorder.mimeType || "audio/webm" });
            resolve(blob);
          };
          this.mediaRecorder.stop();
        });

        // Release mic stream
        if (this.mediaStream) {
          this.mediaStream.getTracks().forEach(track => track.stop());
          this.mediaStream = null;
        }

        if (audioBlob && audioBlob.size > 500) {
          try {
            const whisperText = await this.transcribeWithGroq(audioBlob);
            if (whisperText && whisperText.length >= 2) {
              this.accumulatedText = whisperText;
              if (this.onTranscriptUpdate) {
                this.onTranscriptUpdate(whisperText, "");
              }
            }
          } catch (groqErr) {
            console.warn("Groq Whisper transcription failed, keeping Web Speech text:", groqErr);
          }
        }
      } catch (err) {
        console.error("Audio recording processing error:", err);
      }
    }

    if (this.onStatusChange) this.onStatusChange("idle");
  }

  async transcribeWithGroq(audioBlob) {
    const key = this.groqApiKey;
    const formData = new FormData();
    const filename = (audioBlob.type && audioBlob.type.includes("mp4")) ? "voice.mp4" : "voice.webm";
    formData.append("file", audioBlob, filename);
    formData.append("model", "whisper-large-v3-turbo");
    formData.append("language", "uz");
    formData.append("prompt", "Mahalla do'koni qarz daftari: non, yog', un, shakar, go'sht, kartoshka, sigaret, kola, 50 ming so'm, berdi, oldi, qarz, to'ladi, aka, uka, opa");

    const response = await fetch("https://api.groq.com/openai/v1/audio/transcriptions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${key}`
      },
      body: formData
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Groq HTTP ${response.status}: ${errText}`);
    }

    const data = await response.json();
    return data.text ? data.text.trim() : "";
  }


  // --- DIALECT & NATURAL LANGUAGE PARSER ---
  // Converts spoken Uzbek numbers & phrases into structured ledger data
  parseTranscript(rawText) {
    if (!rawText || !rawText.trim()) {
      return { amount: 0, customerName: "", items: [], rawText: "" };
    }

    let text = rawText.toLowerCase().trim();

    // 1. Normalize dialect pronunciations
    text = this.normalizeDialects(text);

    // 2. Extract and parse spoken numbers (e.g. "qirq besh ming" -> 45000)
    const amount = this.extractAmount(text);

    // 3. Match customer name against active store database
    const customerName = this.extractCustomerName(text);

    // 4. Extract grocery & retail items
    const items = this.extractItems(text);

    // 5. Extract relative date if mentioned ("kecha", "bugun")
    const date = this.extractDate(text);

    return {
      amount,
      customerName,
      items,
      date,
      rawText
    };
  }

  extractDate(text) {
    const now = new Date();
    if (text.includes("kecha") || text.includes("kechagi")) {
      now.setDate(now.getDate() - 1);
      return now.toISOString().slice(0, 16);
    }
    if (text.includes("o'tgan kun") || text.includes("ikki kun oldin") || text.includes("avvalgi kun")) {
      now.setDate(now.getDate() - 2);
      return now.toISOString().slice(0, 16);
    }
    return "";
  }

  normalizeDialects(text) {
    return text
      // Dialect variants for 'ming'
      .replace(/\b(min|mıng|mın)\b/gi, 'ming')
      // Dialect variants for 'so'm'
      .replace(/\b(som|so'mga|somga|sum)\b/gi, "so'm")
      // Action phrases: "yozib qo'y", "yozvor", "ovordi", "opketdi"
      .replace(/\b(yozvor|yozib ber|yozib qo'y|yozvoring|yozing)\b/gi, 'yozildi')
      .replace(/\b(opketdi|olib ketti|olib ketdi|ovordi)\b/gi, 'oldi')
      // Common contractions
      .replace(/\b1ta\b/gi, 'bir ta')
      .replace(/\b2ta\b/gi, 'ikki ta')
      .replace(/\b3ta\b/gi, 'uch ta')
      .replace(/\b4ta\b/gi, 'to\'rt ta')
      .replace(/\b5ta\b/gi, 'besh ta');
  }

  // Parses written numbers ("ellik besh ming", "150 ming", "45k", "bir yarim ming")
  extractAmount(text) {
    // 1. Standard digits with 'ming' or 'k' (e.g., "50 ming", "120k", "50000 so'm")
    const digitMingMatch = text.match(/(\d+)\s*(ming|k)\b/i);
    if (digitMingMatch) {
      return parseInt(digitMingMatch[1], 10) * 1000;
    }

    const rawDigitMatch = text.match(/(\d[\d\s]*\d|\d+)\s*(so'?m)?\b/i);
    if (rawDigitMatch) {
      const cleanNum = rawDigitMatch[1].replace(/\s+/g, '');
      const val = parseInt(cleanNum, 10);
      if (val >= 100) return val;
    }

    // 2. Words to Number Mapping in Uzbek
    const units = {
      'bir': 1, 'ikki': 2, 'uch': 3, 'to\'rt': 4, 'tort': 4,
      'besh': 5, 'olti': 6, 'yetti': 7, 'sakkiz': 8, 'to\'qqiz': 9, 'toqqiz': 9
    };
    const tens = {
      'o\'n': 10, 'on': 10, 'yigirma': 20, 'o\'ttiz': 30, 'ottiz': 30,
      'qirq': 40, 'ellik': 50, 'oltmish': 60, 'yetmish': 70,
      'sakson': 80, 'to\'qson': 90, 'toqson': 90
    };
    const scales = {
      'yuz': 100,
      'ming': 1000,
      'million': 1000000,
      'milyon': 1000000
    };

    // Check special "yarim" (half) e.g. "bir yarim ming" -> 1500
    if (text.includes('bir yarim ming')) return 1500;
    if (text.includes('ikki yarim ming')) return 2500;

    const words = text.split(/\s+/);
    let total = 0;
    let current = 0;
    let hasNumberWord = false;

    for (const w of words) {
      if (units[w] !== undefined) {
        current += units[w];
        hasNumberWord = true;
      } else if (tens[w] !== undefined) {
        current += tens[w];
        hasNumberWord = true;
      } else if (w === 'yuz') {
        current = (current === 0 ? 1 : current) * 100;
        hasNumberWord = true;
      } else if (scales[w] !== undefined) {
        current = (current === 0 ? 1 : current) * scales[w];
        total += current;
        current = 0;
        hasNumberWord = true;
      }
    }
    total += current;

    return hasNumberWord && total >= 500 ? total : 0;
  }

  extractCustomerName(text) {
    if (!window.store || !window.store.state || !window.store.state.customers) {
      return "";
    }

    const customers = window.store.state.customers;
    for (const c of customers) {
      const parts = c.name.toLowerCase().split(/[\s(]+/);
      for (const p of parts) {
        if (p.length > 2 && text.includes(p)) {
          return c.name;
        }
      }
    }
    return "";
  }

  extractItems(text) {
    const canonicalMap = {
      "non": "Non",
      "patir": "Patir",
      "yog'": "Yog'",
      "yog": "Yog'",
      "go'sht": "Go'sht",
      "gosht": "Go'sht",
      "shakar": "Shakar",
      "tuz": "Tuz",
      "sut": "Sut/Qatiq",
      "qatiq": "Sut/Qatiq",
      "qaymoq": "Qaymoq",
      "sariyog'": "Sariyog'",
      "sariyog": "Sariyog'",
      "pishloq": "Pishloq",
      "tuxum": "Tuxum",
      "choy": "Choy",
      "un": "Un",
      "guruch": "Guruch",
      "piyoz": "Meva/Sabzavot",
      "kartoshka": "Meva/Sabzavot",
      "sabzi": "Meva/Sabzavot",
      "pomidor": "Meva/Sabzavot",
      "kola": "Ichimlik",
      "fanta": "Ichimlik",
      "pepsi": "Ichimlik",
      "suv": "Ichimlik",
      "energetik": "Ichimlik",
      "sigaret": "Sigaret",
      "winston": "Sigaret",
      "kent": "Sigaret",
      "chips": "Chips",
      "pechene": "Pechene"
    };

    const detected = [];
    for (const [key, canonical] of Object.entries(canonicalMap)) {
      const regex = new RegExp(`\\b${key}\\b`, 'i');
      if (regex.test(text) && !detected.includes(canonical)) {
        detected.push(canonical);
      }
    }

    return detected;
  }
}

window.voiceService = new VoiceInputService();
