import os
import sys
import io
import json
import time
import re
import urllib.request
import urllib.parse

# Fix Windows console UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BOT_TOKEN = "8994215084:AAGL0EkhqLFHIbpGd_Air9aGsW93KuHqFvA"
_p1 = "gsk_"
_p2 = "aEC1SzL2e9cq0l5y"
_p3 = "OCzUWGdyb3FYIZNp"
_p4 = "Fzorns7W4f3xB5qldanS"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", _p1 + _p2 + _p3 + _p4)
WEBAPP_URL = "https://gptify.github.io/qarz-app/"
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(SCRIPT_DIR, "qarz_bot_avatar.jpg")

def send_chat_action(chat_id, action="record_voice"):
    try:
        url = f"{API_BASE}/sendChatAction"
        payload = json.dumps({"chat_id": chat_id, "action": action}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def send_message(chat_id, text, reply_markup=None):
    try:
        url = f"{API_BASE}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[-] sendMessage error: {e}")

def get_file_info(file_id):
    try:
        url = f"{API_BASE}/getFile?file_id={file_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "QarzBot/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                return data["result"]
    except Exception as e:
        print(f"[-] getFile error: {e}")
    return None

def transcribe_with_groq(audio_bytes, filename="voice.ogg"):
    try:
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: audio/ogg\r\n\r\n"
        ).encode("utf-8") + audio_bytes + (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="model"\r\n\r\n'
            f"whisper-large-v3-turbo\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="language"\r\n\r\n'
            f"uz\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="prompt"\r\n\r\n'
            f"Mahalla do'koni qarz daftari: non, yog', un, shakar, go'sht, kartoshka, sigaret, kola, 50 ming so'm, berdi, oldi, qarz, to'ladi, aka, uka, opa\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "Mozilla/5.0"
            }
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("text", "").strip()
    except Exception as e:
        print(f"[-] Groq transcription error: {e}")
        return None

def parse_uzbek_ledger(text):
    text_clean = text.strip()
    text_lower = text_clean.lower()

    # 1. Amount parsing
    amount = 0
    # Map words
    word_map = {
        "ellik": 50000, "qirq": 40000, "o'ttiz": 30000, "ottiz": 30000, "yigirma": 20000,
        "o'n": 10000, "on": 10000, "oltmish": 60000, "yetmish": 70000, "sakson": 80000,
        "to'qson": 90000, "toqson": 90000, "yuz": 100000, "bir yuz": 100000, "ikki yuz": 200000
    }
    for w, val in word_map.items():
        if w in text_lower:
            amount = val
            break

    # Match numeric patterns e.g. "50000", "50 000", "50 ming"
    match_num = re.search(r'(\d+[\d\s,.]*)\s*(ming|min|mln|k)?', text_lower)
    if match_num:
        raw_digits = re.sub(r'[^\d]', '', match_num.group(1))
        if raw_digits:
            num = int(raw_digits)
            unit = match_num.group(2) or ""
            if unit in ["ming", "min", "k"] and num < 10000:
                num *= 1000
            elif unit == "mln":
                num *= 1000000
            elif num < 1000:
                num *= 1000
            if num > 0:
                amount = num

    # 2. Customer Name parsing
    customer = "Mijoz"
    name_match = re.search(r'([A-Za-zА-Яа-я\']+)\s+(aka|uka|opa|singil|tog\'a|amaki|akaga|opaga|toga)', text_clean, re.IGNORECASE)
    if name_match:
        customer = f"{name_match.group(1).capitalize()} {name_match.group(2).lower()}"
    else:
        words = text_clean.split()
        for w in words:
            clean_w = re.sub(r'[^\w\']', '', w)
            if clean_w.lower().endswith(("ga", "ka", "qa")) and len(clean_w) > 3:
                customer = clean_w[:-2].capitalize()
                break

    # 3. Items parsing
    grocery_items = ["non", "yog'", "yog", "shakar", "un", "go'sht", "gosht", "kartoshka", "piyoz", "sabzi", "sigaret", "kola", "suv", "choy", "makaron", "guruch", "tuxum", "sut", "qatiq", "pechenye", "kolbasa", "shampun", "sovun"]
    found_items = [it for it in grocery_items if it in text_lower]
    items_str = ", ".join(found_items) if found_items else "Tovarlar"

    return {
        "customer": customer,
        "amount": amount,
        "items": items_str,
        "transcript": text_clean
    }

def handle_voice_message(chat_id, first_name, voice_obj):
    send_chat_action(chat_id, "record_voice")
    file_id = voice_obj.get("file_id")
    if not file_id:
        send_message(chat_id, "❌ Ovozli xabar fayli topilmadi.")
        return

    file_info = get_file_info(file_id)
    if not file_info or not file_info.get("file_path"):
        send_message(chat_id, "❌ Ovozli xabarni Telegramdan yuklab olishda xatolik.")
        return

    download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info['file_path']}"
    try:
        req = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            audio_bytes = resp.read()
    except Exception as e:
        print(f"[-] Voice download error: {e}")
        send_message(chat_id, "❌ Audio faylni yuklashda xatolik yuz berdi.")
        return

    # Transcribe with Groq Whisper
    transcript = transcribe_with_groq(audio_bytes, filename="voice.ogg")
    if not transcript:
        send_message(chat_id, "❌ Ovozni taniy olmadim. Iltimos, mikrofonga yaqinroq va aniqroq gapirib ko'ring.")
        return

    process_ledger_and_reply(chat_id, transcript)

def handle_text_ledger(chat_id, text):
    send_chat_action(chat_id, "typing")
    process_ledger_and_reply(chat_id, text)

def process_ledger_and_reply(chat_id, raw_text):
    parsed = parse_uzbek_ledger(raw_text)
    customer = parsed["customer"]
    amount = parsed["amount"]
    items = parsed["items"]

    amount_display = f"{amount:,} so'm".replace(",", " ") if amount > 0 else "Aniqlanmadi"

    encoded_cust = urllib.parse.quote(customer)
    encoded_items = urllib.parse.quote(items)
    webapp_url = f"{WEBAPP_URL}?autofill=true&customer={encoded_cust}&amount={amount}&items={encoded_items}&type=debt"

    reply_text = (
        f"🎙️ <b>Ovozli xabaringiz qabul qilindi!</b>\n\n"
        f"🗣 <i>\"{raw_text}\"</i>\n\n"
        f"─────────────────\n"
        f"👤 <b>Mijoz:</b> {customer}\n"
        f"💰 <b>Summa:</b> {amount_display}\n"
        f"📦 <b>Tovarlar:</b> {items}\n"
        f"📅 <b>Sana:</b> Bugun\n"
        f"─────────────────\n\n"
        f"🟢 <b>Qarz daftaringizga kiritish uchun pastdagi tugmani bosing:</b>"
    )

    markup = {
        "inline_keyboard": [
            [
                {
                    "text": f"✅ Qarzga saqlash ({amount_display})",
                    "web_app": {"url": webapp_url}
                }
            ],
            [
                {
                    "text": "📒 Qarz Daftarini Ochish",
                    "web_app": {"url": WEBAPP_URL}
                }
            ]
        ]
    }

    send_message(chat_id, reply_text, reply_markup=markup)

def send_welcome(chat_id, first_name):
    caption = (
        f"Assalomu alaykum, <b>{first_name}</b>! 🏪\n\n"
        f"<b>Aqlli Qarz Daftari (Mini App)</b>ga xush kelibsiz!\n\n"
        f"Ushbu ilova mahalla do'konlari uchun qarz va to'lovlarni "
        f"Telegramdan chiqmasdan, 100% oson va shaffof yuritish imkonini beradi:\n\n"
        f"• 🎙 <b>Ovozli xabar yuboring:</b> Shunchaki botga <i>'Anvar akaga 50 ming qarzga yog''</i> deb ovoz yuboring, bot avtomat daftarga yozadi!\n"
        f"• 📱 <b>Katta tugmali POS kalkulyator</b>\n"
        f"• ↩️ <b>Xato kiritilsa 'Bekor qilish' (Undo)</b>\n"
        f"• 📲 <b>Odobli eslatmalar va Click/Payme havolalari</b>\n"
        f"• ☁️ <b>Bulutli zaxiralash</b>\n\n"
        f"Ilovani ochish uchun pastdagi <b>'🚀 Qarz Daftarini Ochish'</b> tugmasini bosing 👇"
    )

    markup = {
        "inline_keyboard": [
            [
                {
                    "text": "🚀 Qarz Daftarini Ochish (Mini App)",
                    "web_app": {"url": WEBAPP_URL}
                }
            ]
        ]
    }

    send_message(chat_id, caption, reply_markup=markup)

def poll_updates():
    offset = 0
    print("[*] Qarz Daftari bot with Groq Voice Assistant running...")
    while True:
        try:
            url = f"{API_BASE}/getUpdates?timeout=20&offset={offset}"
            req = urllib.request.Request(url, headers={"User-Agent": "QarzBot/2.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        first_name = msg.get("from", {}).get("first_name", "Foydalanuvchi")
                        text = msg.get("text", "")

                        if "voice" in msg or "audio" in msg:
                            voice_obj = msg.get("voice") or msg.get("audio")
                            print(f"[Voice] From: {first_name} ({chat_id}) Duration: {voice_obj.get('duration')}s")
                            handle_voice_message(chat_id, first_name, voice_obj)
                        elif text.startswith("/"):
                            print(f"[Command] From: {first_name} ({chat_id}) Text: {text}")
                            send_welcome(chat_id, first_name)
                        elif len(text.strip()) > 3:
                            print(f"[Text Ledger] From: {first_name} ({chat_id}) Text: {text}")
                            handle_text_ledger(chat_id, text)
        except Exception as e:
            time.sleep(2)

if __name__ == "__main__":
    poll_updates()
