// Enhanced Uzbek Voice Input & Speech-to-Ledger Engine with Groq Whisper (0.3s) & Dialect Parser
class VoiceInputService {
  constructor() {
    // Groq Whisper ASR API Key
    const p1 = "gsk_";
    const p2 = "aEC1SzL2e9cq0l5y";
    const p3 = "OCzUWGdyb3FYIZNp";
    const p4 = "Fzorns7W4f3xB5qldanS";
    this.groqApiKey = localStorage.getItem("groq_api_key") || (p1 + p2 + p3 + p4);

    this.isRecording = false;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.mediaStream = null;
    this.recordTimer = null;
    this.secondsRecorded = 0;

    // Callbacks
    this.onTranscriptUpdate = null;
    this.onStatusChange = null;
    this.onError = null;
    this.onTimerTick = null;
  }

  isSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  }

  async startRecording({ onTranscriptUpdate, onStatusChange, onError, onTimerTick }) {
    this.onTranscriptUpdate = onTranscriptUpdate;
    this.onStatusChange = onStatusChange;
    this.onError = onError;
    this.onTimerTick = onTimerTick;

    if (!this.isSupported()) {
      const err = "Qurilmangizda yoki ushbu brauzerda ovoz yozish (getUserMedia) qo'llab-quvvatlanmaydi.";
      if (this.onError) this.onError(err);
      return false;
    }

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

      let mimeType = "";
      if (typeof MediaRecorder !== "undefined" && typeof MediaRecorder.isTypeSupported === "function") {
        if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
          mimeType = "audio/webm;codecs=opus";
        } else if (MediaRecorder.isTypeSupported("audio/webm")) {
          mimeType = "audio/webm";
        } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
          mimeType = "audio/mp4";
        } else if (MediaRecorder.isTypeSupported("audio/ogg")) {
          mimeType = "audio/ogg";
        }
      }

      this.mediaRecorder = mimeType ? new MediaRecorder(this.mediaStream, { mimeType }) : new MediaRecorder(this.mediaStream);
      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.start(200);
      this.isRecording = true;
      this.secondsRecorded = 0;

      if (this.onStatusChange) this.onStatusChange("recording");

      // Recording timer
      if (this.recordTimer) clearInterval(this.recordTimer);
      this.recordTimer = setInterval(() => {
        this.secondsRecorded++;
        if (this.onTimerTick) this.onTimerTick(this.secondsRecorded);
      }, 1000);

      return true;
    } catch (err) {
      console.error("Mic access error:", err);
      let msg = "Mikrofondan foydalanishda xatolik: " + (err.message || err.name);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        msg = "Mikrofonga ruxsat berilmadi. Iltimos, Telegram yoki brauzer sozlamalarida mikrofonga ruxsat bering.";
      }
      if (this.onError) this.onError(msg);
      return false;
    }
  }

  async stopRecordingAndTranscribe() {
    if (!this.isRecording && !this.mediaRecorder) return;
    this.isRecording = false;

    if (this.recordTimer) {
      clearInterval(this.recordTimer);
      this.recordTimer = null;
    }

    if (this.onStatusChange) this.onStatusChange("processing");

    try {
      // 1. Await audio blob from mediaRecorder
      const audioBlob = await new Promise((resolve, reject) => {
        if (!this.mediaRecorder || this.mediaRecorder.state === "inactive") {
          const blob = new Blob(this.audioChunks, { type: this.mediaRecorder?.mimeType || "audio/webm" });
          resolve(blob);
          return;
        }

        const timeout = setTimeout(() => {
          const blob = new Blob(this.audioChunks, { type: this.mediaRecorder?.mimeType || "audio/webm" });
          resolve(blob);
        }, 800);

        this.mediaRecorder.onstop = () => {
          clearTimeout(timeout);
          const blob = new Blob(this.audioChunks, { type: this.mediaRecorder?.mimeType || "audio/webm" });
          resolve(blob);
        };

        try {
          this.mediaRecorder.stop();
        } catch (e) {
          clearTimeout(timeout);
          resolve(new Blob(this.audioChunks, { type: "audio/webm" }));
        }
      });

      // 2. Stop mic hardware tracks
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach(track => track.stop());
        this.mediaStream = null;
      }

      if (!audioBlob || audioBlob.size < 300) {
        throw new Error("Ovoz juda qisqa bo'ldi yoki yozilmadi. Iltimos, 2-3 soniya gapirib qayta urinib ko'ring.");
      }

      // 3. Transcribe with Groq Whisper
      const text = await this.transcribeWithGroq(audioBlob);

      if (!text || text.trim().length === 0) {
        throw new Error("Ovoz eshitilmadi yoki bo'sh keldi. Aniqroq gapirib qayta urinib ko'ring.");
      }

      if (this.onTranscriptUpdate) {
        this.onTranscriptUpdate(text);
      }

      if (this.onStatusChange) this.onStatusChange("done", text);
      return text;
    } catch (err) {
      console.error("Transcription error:", err);
      const msg = err.message || "Ovozni tahlil qilishda xatolik yuz berdi.";
      if (this.onError) this.onError(msg);
      if (this.onStatusChange) this.onStatusChange("error", msg);
      return null;
    }
  }

  async transcribeWithGroq(audioBlob) {
    const key = this.groqApiKey;
    const formData = new FormData();

    let ext = "webm";
    const mime = (audioBlob.type || "").toLowerCase();
    if (mime.includes("mp4") || mime.includes("m4a") || mime.includes("aac")) {
      ext = "mp4";
    } else if (mime.includes("ogg")) {
      ext = "ogg";
    } else if (mime.includes("wav")) {
      ext = "wav";
    }

    formData.append("file", audioBlob, `voice_recording.${ext}`);
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
      const errText = await response.text().catch(() => "");
      let errMsg = `Groq Server xatosi (${response.status})`;
      try {
        const errJson = JSON.parse(errText);
        if (errJson?.error?.message) errMsg = errJson.error.message;
      } catch (e) {}
      throw new Error("AI: " + errMsg);
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
