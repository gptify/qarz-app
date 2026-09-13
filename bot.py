import os
import sys
import io
import json
import time
import urllib.request

# Fix Windows console UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BOT_TOKEN = "8994215084:AAGL0EkhqLFHIbpGd_Air9aGsW93KuHqFvA"
WEBAPP_URL = "https://gptify.github.io/qarz-app/"
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(SCRIPT_DIR, "qarz_bot_avatar.jpg")

def send_welcome(chat_id, first_name):
    caption = (
        f"Assalomu alaykum, <b>{first_name}</b>! 🏪\n\n"
        f"<b>Aqlli Qarz Daftari (Mini App)</b>ga xush kelibsiz!\n\n"
        f"Ushbu ilova mahalla do'konlari uchun qarz va to'lovlarni "
        f"Telegramdan chiqmasdan, 100% oson va shaffof yuritish imkonini beradi:\n\n"
        f"• 🎙 <b>Ovozli qarz yozish</b> (to'xtovsiz rejimda)\n"
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

    # Also set persistent keyboard
    reply_kb = {
        "keyboard": [
            [
                {
                    "text": "📒 Qarz Daftarini Ochish",
                    "web_app": {"url": WEBAPP_URL}
                }
            ]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

    # Try sending photo first
    if os.path.exists(LOGO_PATH):
        try:
            import mimetypes
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            body = []
            body.append(f"--{boundary}".encode())
            body.append(f'Content-Disposition: form-data; name="chat_id"'.encode())
            body.append(b"")
            body.append(str(chat_id).encode())
            
            body.append(f"--{boundary}".encode())
            body.append(f'Content-Disposition: form-data; name="caption"'.encode())
            body.append(b"")
            body.append(caption.encode("utf-8"))
            
            body.append(f"--{boundary}".encode())
            body.append(f'Content-Disposition: form-data; name="parse_mode"'.encode())
            body.append(b"")
            body.append(b"HTML")
            
            body.append(f"--{boundary}".encode())
            body.append(f'Content-Disposition: form-data; name="reply_markup"'.encode())
            body.append(b"")
            body.append(json.dumps(markup).encode("utf-8"))
            
            with open(LOGO_PATH, "rb") as f:
                photo_bytes = f.read()
            body.append(f"--{boundary}".encode())
            body.append(f'Content-Disposition: form-data; name="photo"; filename="logo.jpg"'.encode())
            body.append(b"Content-Type: image/jpeg")
            body.append(b"")
            body.append(photo_bytes)
            body.append(f"--{boundary}--".encode())
            body.append(b"")
            
            req = urllib.request.Request(
                f"{API_BASE}/sendPhoto",
                data=b"\r\n".join(body),
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
            )
            urllib.request.urlopen(req)
            print(f"[+] Sent photo welcome to {chat_id}")
            return
        except Exception as e:
            print(f"[-] sendPhoto error: {e}")

    # Fallback to text
    payload = {
        "chat_id": chat_id,
        "text": caption,
        "parse_mode": "HTML",
        "reply_markup": markup
    }
    req = urllib.request.Request(f"{API_BASE}/sendMessage", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)

def poll_updates():
    offset = 0
    print("[*] Qarz Daftari bot polling running...")
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
                        print(f"[Update] From: {first_name} ({chat_id}) Text: {text}")
                        send_welcome(chat_id, first_name)
        except Exception as e:
            time.sleep(2)

if __name__ == "__main__":
    poll_updates()
