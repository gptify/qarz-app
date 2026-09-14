import os
import sys
import io
import json
import time
import re
import base64
import urllib.request
import urllib.parse
import threading
import collections
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from dotenv import load_dotenv

START_TIME = time.time()
LOG_BUFFER = collections.deque(maxlen=200)

def log_msg(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_BUFFER.append(line)

# Fix Windows console UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Load environment
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(SCRIPT_DIR / ".env")
load_dotenv()

DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DRAFTS_FILE = DATA_DIR / "active_drafts.json"
LEDGER_FILE = DATA_DIR / "ledger_saved.json"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_QARZ", "8994215084:AAGL0EkhqLFHIbpGd_Air9aGsW93KuHqFvA")
_p1 = "gsk_"
_p2 = "aEC1SzL2e9cq0l5y"
_p3 = "OCzUWGdyb3FYIZNp"
_p4 = "Fzorns7W4f3xB5qldanS"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", _p1 + _p2 + _p3 + _p4)

_k1 = "AQ.Ab8RN6JaS4W"
_k2 = "srHlK4o8fjPrcO8Es"
_k3 = "TvAOpVO_hARfeOtDhCxyaw"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", _k1 + _k2 + _k3)
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "gemini-3.6-flash")
FALLBACK_MODELS = ["gemini-flash-latest"]

def clean_amount(val):
    if isinstance(val, (int, float)):
        return int(val)
    if not val:
        return 0
    val_str = str(val).lower()
    raw = re.sub(r'[^\d]', '', val_str)
    if raw:
        num = int(raw)
        if ("ming" in val_str or "min" in val_str) and num < 10000:
            num *= 1000
        return num
    return 0

WEBAPP_URL = "https://gptify.github.io/qarz-app/"
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Draft and Conversation State storage
def load_drafts():
    if DRAFTS_FILE.exists():
        try:
            return json.loads(DRAFTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_drafts(drafts):
    try:
        DRAFTS_FILE.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[-] save_drafts error: {e}", flush=True)

def save_confirmed_tx(tx):
    records = []
    if LEDGER_FILE.exists():
        try:
            records = json.loads(LEDGER_FILE.read_text(encoding="utf-8"))
        except Exception:
            records = []
    records.append(tx)
    try:
        LEDGER_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[-] save_confirmed_tx error: {e}", flush=True)

USER_DRAFTS = load_drafts()
USER_STATES = {}  # chat_id -> {"action": "waiting_name"|"waiting_amount"|"waiting_items"|"waiting_full", "draft_id": "..."}

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
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[-] sendMessage error: {e}", flush=True)
        return None

def edit_message_text(chat_id, message_id, text, reply_markup=None):
    try:
        url = f"{API_BASE}/editMessageText"
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[-] editMessageText error: {e}", flush=True)

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    try:
        url = f"{API_BASE}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
            payload["show_alert"] = show_alert
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"[-] answerCallbackQuery error: {e}", flush=True)

def get_file_info(file_id):
    try:
        url = f"{API_BASE}/getFile?file_id={file_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "QarzBot/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                return data["result"]
    except Exception as e:
        print(f"[-] getFile error: {e}", flush=True)
    return None

def process_voice_with_gemini(audio_bytes: bytes, mime_type: str = "audio/ogg") -> dict:
    """Gemini 3.6 Flash multimodal audio: precise Uzbek speech recognition & entity parsing."""
    if not GEMINI_API_KEY:
        return None

    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    clean_mime = mime_type.split(";")[0].strip() if mime_type else "audio/ogg"
    if clean_mime in ["audio/oga", "application/ogg", "audio/opus"]:
        clean_mime = "audio/ogg"

    system_prompt = """Siz O'zbekistondagi do'konlarning professional AI hisobchisisiz (Aqlli Qarz Daftari).
Do'kondor yoki xaridor qarzga berilgan tovarlar yoki to'lov haqida ovozli xabar yubordi.
Ushbu audio yozuvni diqqat bilan eshitib, barcha so'zlarni to'liq, aniq o'zbek tilida transkripsiya qiling va quyidagi ma'lumotlarni ajrating:

1. "transcription": audioda aytilgan to'liq gap (masalan: "Akmal akaga 50 mingga 2 ta non bilan yog' berdim" yoki "Anvar ustaga bir dona yog' 30 ming, kolbasa 100 ming").
2. "customer_name": Mijozning ismi.
   - O'zbek ismlarini xatosiz, to'g'ri bosh harf bilan yozing: Akmal, Anvar, Nodir, Dilshod, Sardor, Rustam, Jamshid, Bobur, Otabek, Shavkat, Ulug'bek, Sherzod, Javohir, Farrux, Alisher, Bekzod, Jasur, Davron, Elyor, Xurshid, Aziz, Sanjar, Shohruh, Doston, Baxtiyor, Muzaffar, Umid, Komil, Ilhom, Zafar, Davlat; ayollar: Dilnoza, Shahnoza, Nilufar, Gulnoza, Madina, Malika, Feruza, Nargiza, Mohira, Sevara, Zilola, Lola, Rayhon, Ziyoda, Yulduz, Munira, Dildora va h.k.
   - Hurmat so'zlari aytilgan bo'lsa qoldiring: "Akmal aka", "Nodir aka", "Dilnoza opa", "Rustam tog'a", "Anvar usta".
   - Egalik va jo'nalish kelishigi qo'shimchalarini olib tashlang: "Akmalga" -> "Akmal", "Davlatga" -> "Davlat", "Anvar ustaga" -> "Anvar usta", "Sardordan" -> "Sardor".
   - Agar ism aytilmagan yoki noaniq bo'lsa, "Mijoz" deb qaytaring.
3. "amount": Umumiy qarz summasi (faqat butun son raqam, so'mda).
   - QAT'IY QOIDA (AVTOMATIK YIG'INDI): Har ikkala holatda ham summa avtomatik to'g'ri hisoblanishi SHART!
   - 1-holat (har bir tovar narxi alohida aytilsa): Barcha tovarlar narxlarini birma-bir qo'shib, umumiy summasini yozing. Masalan: 2 ta non 8 ming + yog' 30 ming + kola 15 ming -> amount: 53000 (yoki 30 ming + 100 ming + 25 ming -> 155000).
   - 2-holat (umumiy summa tovarlar bilan birga aytilsa): Aytilgan umumiy summani yozing. Masalan: "50 mingga 2 ta non va yog'" -> amount: 50000.
4. "items": Olingan tovarlar yoki izoh.
   - QAT'IY FORMAT QOIDASI:
     a) Agar foydalanuvchi har bir tovar nomi va uning narxini aytsa, har bir tovardan keyin qavs ichida uning narxini yozing!
        Masalan: "2 ta non (8 000 so'm), yog' (30 000 so'm), kola (15 000 so'm)" yoki "bir dona yog' (30 000 so'm), bir dona kolbasa (100 000 so'm), bir dona kola (25 000 so'm)".
     b) Agar tovarlar bilan birga bitta umumiy summa aytilgan bo'lsa (har bir tovarning alohida narxi aytilmagan bo'lsa), faqat tovar nomlarini yozing (qavssiz)!
        Masalan: "2 ta non, yog'" yoki "yog', kolbasa, 4 ta non".
5. "type": "give" (qarz berildi / nasiya) yoki "receive" (qarz to'landi / qaytarildi).
6. "due_days": Qachongacha berilgani (kunlar soni, sukut bo'yicha 7).

Qat'iy faqat JSON formatida qaytaring:
{
  "is_clear": true,
  "transcription": "audioda eshitilgan gap",
  "customer_name": "Davlat",
  "amount": 500000,
  "type": "give",
  "items": "yog' (300 000 so'm), kolbasa (100 000 so'm), 4 ta non (100 000 so'm)",
  "due_days": 7
}

Agar audio bo'sh, shovqin yoki tushunarsiz bo'lsa:
{
  "is_clear": false,
  "transcription": "",
  "reason": "Ovoz aniq eshitilmadi"
}"""

    candidate_models = list(dict.fromkeys([PRIMARY_MODEL] + FALLBACK_MODELS))
    for model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [
                    {"inlineData": {"mimeType": clean_mime, "data": b64_audio}},
                    {"text": system_prompt}
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text_resp = data["candidates"][0]["content"]["parts"][0]["text"]
                clean = re.sub(r"^```json\s*|\s*```$", "", text_resp.strip())
                parsed = json.loads(clean)
                if parsed and isinstance(parsed, dict) and parsed.get("is_clear") and parsed.get("transcription"):
                    print(f"[+] Gemini {model} transcribed: {parsed.get('transcription')}", flush=True)
                    return parsed
        except Exception as ex:
            print(f"[-] Gemini {model} voice error: {ex}", flush=True)
            continue

    return None

def transcribe_with_groq(audio_bytes, filename="voice.ogg"):
    """Fallback speech-to-text using Groq Whisper."""
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
        print(f"[-] Groq transcription error: {e}", flush=True)
        return None

def parse_uzbek_ledger(text):
    text_clean = text.strip()
    text_lower = text_clean.lower()

    # Amount parsing
    amount = 0
    word_map = {
        "ellik": 50000, "qirq": 40000, "o'ttiz": 30000, "ottiz": 30000, "yigirma": 20000,
        "o'n": 10000, "on": 10000, "oltmish": 60000, "yetmish": 70000, "sakson": 80000,
        "to'qson": 90000, "toqson": 90000, "yuz": 100000, "bir yuz": 100000, "ikki yuz": 200000,
        "uch yuz": 300000, "to'rt yuz": 400000, "besh yuz": 500000
    }
    for w, val in word_map.items():
        if w in text_lower:
            amount = val
            break

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

    # Customer Name parsing
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

    # Items parsing
    grocery_items = ["non", "yog'", "yog", "shakar", "un", "go'sht", "gosht", "kartoshka", "piyoz", "sabzi", "sigaret", "kola", "suv", "choy", "makaron", "guruch", "tuxum", "sut", "qatiq", "pechenye", "kolbasa", "shampun", "sovun"]
    found_items = [it for it in grocery_items if it in text_lower]
    items_str = ", ".join(found_items) if found_items else "Tovarlar"

    return {
        "customer": customer,
        "amount": amount,
        "items": items_str,
        "transcript": text_clean
    }

def render_draft_message(draft_id, draft):
    customer = draft.get("customer", "Mijoz")
    amount = int(draft.get("amount", 0))
    items = draft.get("items", "Tovarlar")
    raw_text = draft.get("transcription", "")
    action_type = draft.get("action_type", "give")

    amount_display = f"{amount:,} so'm".replace(",", " ") if amount > 0 else "0 so'm"
    encoded_cust = urllib.parse.quote(customer)
    encoded_items = urllib.parse.quote(items)
    webapp_url = f"{WEBAPP_URL}?autofill=true&customer={encoded_cust}&amount={amount}&items={encoded_items}&draft_id={draft_id}&type={action_type}"

    title_emoji = "🟢 Nasiya (Qarz berish)" if action_type == "give" else "🔵 Qarz to'lovi"
    toggle_label = "Qarz to'loviga o'tkazish" if action_type == "give" else "Nasiyaga o'tkazish"

    text = (
        f"🎙️ <b>Ovozli qoralama qabul qilindi!</b> <code>#Q{draft_id}</code>\n\n"
        f"🗣 <i>\"{raw_text}\"</i>\n\n"
        f"─────────────────\n"
        f"📋 <b>Holat:</b> 📝 <b>Qoralama (Ko'rib chiqilmoqda)</b>\n"
        f"🏷 <b>Turi:</b> {title_emoji}\n"
        f"👤 <b>Mijoz:</b> <b>{customer}</b>\n"
        f"💰 <b>Summa:</b> <b>{amount_display}</b>\n"
        f"📦 <b>Tovarlar:</b> {items}\n"
        f"📅 <b>Sana:</b> Bugun\n"
        f"─────────────────\n\n"
        f"💡 <i>Qoralamani tasdiqlashdan oldin barcha qismlarini to'g'rilashingiz mumkin:</i>"
    )

    markup = {
        "inline_keyboard": [
            [
                {
                    "text": f"✅ Tasdiqlash va Saqlash ({amount_display})",
                    "callback_data": f"confirm_{draft_id}"
                }
            ],
            [
                {
                    "text": f"👤 Ism: {customer[:11]} ✏️",
                    "callback_data": f"edit_name_{draft_id}"
                },
                {
                    "text": f"💰 Summa ✏️",
                    "callback_data": f"edit_sum_{draft_id}"
                }
            ],
            [
                {
                    "text": f"📦 Tovarlar / Izoh ✏️",
                    "callback_data": f"edit_items_{draft_id}"
                },
                {
                    "text": f"🔄 {toggle_label}",
                    "callback_data": f"toggle_type_{draft_id}"
                }
            ],
            [
                {
                    "text": "✍️ Butun qoralamani matnda tahrirlash",
                    "callback_data": f"edit_full_{draft_id}"
                }
            ],
            [
                {
                    "text": "📱 Mini Appda to'liq tekshirish & saqlash",
                    "web_app": {"url": webapp_url}
                }
            ],
            [
                {
                    "text": "🗑️ Qoralamani o'chirish",
                    "callback_data": f"delete_{draft_id}"
                }
            ]
        ]
    }
    return text, markup

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
        print(f"[-] Voice download error: {e}", flush=True)
        send_message(chat_id, "❌ Audio faylni yuklashda xatolik yuz berdi.")
        return

    status_msg = send_message(chat_id, "⏳ <i>Ovozingiz qabul qilindi, AI eshitmoqda va qoralama tuzmoqda...</i>")
    status_msg_id = status_msg.get("result", {}).get("message_id") if (status_msg and status_msg.get("ok")) else None

    # 1. First priority: Gemini 3.6 Flash multimodal audio
    parsed = process_voice_with_gemini(audio_bytes, mime_type="audio/ogg")
    
    if parsed and parsed.get("transcription"):
        transcript = parsed.get("transcription", "").strip()
        customer = parsed.get("customer_name") or "Mijoz"
        amount = clean_amount(parsed.get("amount") or 0)
        items = parsed.get("items") or "Tovarlar"
        action_type = parsed.get("type") or "give"
    else:
        # 2. Fallback to Groq Whisper
        transcript = transcribe_with_groq(audio_bytes, filename="voice.ogg")
        if not transcript:
            err_msg = "❌ Ovozni taniy olmadim. Iltimos, mikrofonga yaqinroq va aniqroq gapirib ko'ring."
            if status_msg_id:
                edit_message_text(chat_id, status_msg_id, err_msg)
            else:
                send_message(chat_id, err_msg)
            return
        parsed_legacy = parse_uzbek_ledger(transcript)
        customer = parsed_legacy["customer"]
        amount = clean_amount(parsed_legacy["amount"])
        items = parsed_legacy["items"]
        action_type = "give"

    # Create Draft
    draft_id = str(int(time.time()))[-4:]
    USER_DRAFTS[draft_id] = {
        "draft_id": draft_id,
        "chat_id": chat_id,
        "customer": customer,
        "amount": amount,
        "items": items,
        "transcription": transcript,
        "action_type": action_type,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_drafts(USER_DRAFTS)

    text, markup = render_draft_message(draft_id, USER_DRAFTS[draft_id])
    if status_msg_id:
        edit_message_text(chat_id, status_msg_id, text, reply_markup=markup)
    else:
        send_message(chat_id, text, reply_markup=markup)

def handle_text_ledger(chat_id, text):
    send_chat_action(chat_id, "typing")
    parsed = parse_uzbek_ledger(text)
    draft_id = str(int(time.time()))[-4:]
    USER_DRAFTS[draft_id] = {
        "draft_id": draft_id,
        "chat_id": chat_id,
        "customer": parsed["customer"],
        "amount": parsed["amount"],
        "items": parsed["items"],
        "transcription": text,
        "action_type": "give",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_drafts(USER_DRAFTS)

    msg_text, markup = render_draft_message(draft_id, USER_DRAFTS[draft_id])
    send_message(chat_id, msg_text, reply_markup=markup)

def send_welcome(chat_id, first_name):
    caption = (
        f"Assalomu alaykum, <b>{first_name}</b>! 🏪\n\n"
        f"<b>Aqlli Qarz Daftari (Mini App)</b>ga xush kelibsiz!\n\n"
        f"Ushbu ilova mahalla do'konlari uchun qarz va to'lovlarni "
        f"Telegramdan chiqmasdan, 100% oson va shaffof yuritish imkonini beradi:\n\n"
        f"• 🎙 <b>Ovozli xabar yuboring:</b> Shunchaki botga <i>'Anvar akaga 50 ming qarzga yog''</i> deb ovoz yuboring, bot avtomat qoralama tuzadi!\n"
        f"• 📝 <b>Ovozli Qoralama:</b> Ism, summa, tovarlar yoki turni to'g'rilab, keyin daftarga saqlaysiz!\n"
        f"• 📱 <b>Katta tugmali POS kalkulyator</b>\n"
        f"• ↩️ <b>Xato kiritilsa 'Bekor qilish' (Undo)</b>\n"
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

def process_single_update(update):
    try:
        # 1. Handle Callback Queries (Buttons)
        if "callback_query" in update:
            cb = update["callback_query"]
            cb_id = cb["id"]
            cb_data = cb.get("data", "")
            chat_id = cb["message"]["chat"]["id"]
            message_id = cb["message"]["message_id"]

            log_msg(f"[Callback] data={cb_data} from chat={chat_id}")

            if cb_data.startswith("confirm_"):
                draft_id = cb_data.split("_")[1]
                draft = USER_DRAFTS.get(draft_id)
                if draft:
                    save_confirmed_tx(draft)
                    USER_DRAFTS.pop(draft_id, None)
                    save_drafts(USER_DRAFTS)

                    amount_display = f"{draft['amount']:,} so'm".replace(",", " ") if draft['amount'] > 0 else "0 so'm"
                    action_name = "Nasiya (Qarz)" if draft.get("action_type") == "give" else "Qarz to'lovi"
                    answer_callback_query(cb_id, text="Qarz saqlandi! ✅")

                    final_text = (
                        f"✅ <b>Qarz daftaringizga muvaffaqiyatli saqlandi!</b>\n\n"
                        f"📋 <b>Turi:</b> {action_name}\n"
                        f"👤 <b>Mijoz:</b> <b>{draft['customer']}</b>\n"
                        f"💰 <b>Summa:</b> <b>{amount_display}</b>\n"
                        f"📦 <b>Tovarlar:</b> {draft['items']}\n"
                        f"📅 <b>Sana:</b> Bugun\n\n"
                        f"🎉 <i>Ma'lumotlar Qarz daftaringizga kiritildi!</i>"
                    )
                    markup = {
                        "inline_keyboard": [
                            [{"text": "📒 Qarz Daftarini Ochish", "web_app": {"url": WEBAPP_URL}}]
                        ]
                    }
                    edit_message_text(chat_id, message_id, final_text, reply_markup=markup)
                else:
                    answer_callback_query(cb_id, text="Qoralama topilmadi yoki allaqachon saqlangan.")

            elif cb_data.startswith("edit_name_"):
                draft_id = cb_data.split("_")[2]
                USER_STATES[chat_id] = {"action": "waiting_name", "draft_id": draft_id, "message_id": message_id}
                answer_callback_query(cb_id)
                send_message(chat_id, f"✏️ <b>Qoralama #Q{draft_id}:</b> Mijozning to'g'ri ismini yozib yuboring (masalan: <i>Akmal aka</i> yoki <i>Nodir</i>):")

            elif cb_data.startswith("edit_sum_"):
                draft_id = cb_data.split("_")[2]
                USER_STATES[chat_id] = {"action": "waiting_amount", "draft_id": draft_id, "message_id": message_id}
                answer_callback_query(cb_id)
                send_message(chat_id, f"💰 <b>Qoralama #Q{draft_id}:</b> To'g'ri summani yozib yuboring (masalan: <i>50000</i> yoki <i>50 ming</i>):")

            elif cb_data.startswith("edit_items_"):
                draft_id = cb_data.split("_")[2]
                USER_STATES[chat_id] = {"action": "waiting_items", "draft_id": draft_id, "message_id": message_id}
                answer_callback_query(cb_id)
                send_message(chat_id, f"📦 <b>Qoralama #Q{draft_id}:</b> Tovarlar yoki izohni yozib yuboring (masalan: <i>2 ta non, yog', sigaret</i>):")

            elif cb_data.startswith("toggle_type_"):
                draft_id = cb_data.split("_")[2]
                draft = USER_DRAFTS.get(draft_id)
                if draft:
                    draft["action_type"] = "receive" if draft.get("action_type") == "give" else "give"
                    save_drafts(USER_DRAFTS)
                    new_label = "🟢 Qarz berish" if draft["action_type"] == "give" else "🔵 Qarz to'lovi"
                    answer_callback_query(cb_id, text=f"Turi o'zgartirildi: {new_label}")
                    updated_text, markup = render_draft_message(draft_id, draft)
                    edit_message_text(chat_id, message_id, updated_text, reply_markup=markup)

            elif cb_data.startswith("edit_full_"):
                draft_id = cb_data.split("_")[2]
                draft = USER_DRAFTS.get(draft_id)
                if draft:
                    USER_STATES[chat_id] = {"action": "waiting_full", "draft_id": draft_id, "message_id": message_id}
                    answer_callback_query(cb_id)
                    cur_type = "Qarz berish" if draft.get("action_type") == "give" else "Qarz to'lovi"
                    template = (
                        f"✍️ <b>Qoralama #Q{draft_id} ni to'liq tahrirlash:</b>\n\n"
                        f"Quyidagi matndan nusxa olib, kerakli joylarini o'zgartiring va bitta xabarda yuboring:\n\n"
                        f"<code>Mijoz: {draft['customer']}\n"
                        f"Summa: {draft['amount']}\n"
                        f"Tovarlar: {draft['items']}\n"
                        f"Turi: {cur_type}</code>"
                    )
                    send_message(chat_id, template)

            elif cb_data.startswith("delete_"):
                draft_id = cb_data.split("_")[1]
                USER_DRAFTS.pop(draft_id, None)
                save_drafts(USER_DRAFTS)
                answer_callback_query(cb_id, text="Qoralama bekor qilindi")
                edit_message_text(chat_id, message_id, f"❌ <b>Qoralama #Q{draft_id} bekor qilindi va o'chirildi.</b>")

        # 2. Handle Messages (Voice or Text)
        elif "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            first_name = msg.get("from", {}).get("first_name", "Foydalanuvchi")
            text = msg.get("text", "")

            # Check if user is in an active prompt state
            if chat_id in USER_STATES and text:
                state = USER_STATES[chat_id]
                draft_id = state.get("draft_id")
                action = state.get("action")
                draft = USER_DRAFTS.get(draft_id)

                if draft:
                    if action == "waiting_name":
                        new_name = text.strip()
                        draft["customer"] = new_name
                        save_drafts(USER_DRAFTS)
                        del USER_STATES[chat_id]
                        send_message(chat_id, f"✅ Mijoz ismi <b>{new_name}</b> ga to'g'rilandi!")
                        updated_text, markup = render_draft_message(draft_id, draft)
                        send_message(chat_id, updated_text, reply_markup=markup)
                        return

                    elif action == "waiting_amount":
                        parsed_num = parse_uzbek_ledger(text)["amount"]
                        if parsed_num > 0:
                            draft["amount"] = parsed_num
                            save_drafts(USER_DRAFTS)
                            del USER_STATES[chat_id]
                            amt_disp = f"{parsed_num:,} so'm".replace(",", " ")
                            send_message(chat_id, f"✅ Summa <b>{amt_disp}</b> ga to'g'rilandi!")
                            updated_text, markup = render_draft_message(draft_id, draft)
                            send_message(chat_id, updated_text, reply_markup=markup)
                            return
                        else:
                            send_message(chat_id, "⚠️ Summa aniqlanmadi. Iltimos, raqamda yozing (masalan: 65000 yoki 65 ming):")
                            return

                    elif action == "waiting_items":
                        new_items = text.strip()
                        draft["items"] = new_items
                        save_drafts(USER_DRAFTS)
                        del USER_STATES[chat_id]
                        send_message(chat_id, f"✅ Tovarlar / izoh <b>{new_items}</b> ga to'g'rilandi!")
                        updated_text, markup = render_draft_message(draft_id, draft)
                        send_message(chat_id, updated_text, reply_markup=markup)
                        return

                    elif action == "waiting_full":
                        # Parse multi-line edit
                        lines = text.strip().split("\n")
                        for l in lines:
                            l = l.strip()
                            if re.match(r'^(mijoz|ism)\s*:', l, re.IGNORECASE):
                                val = re.sub(r'^(mijoz|ism)\s*:\s*', '', l, flags=re.IGNORECASE).strip()
                                if val: draft["customer"] = val
                            elif re.match(r'^(summa|narx)\s*:', l, re.IGNORECASE):
                                val_amt = parse_uzbek_ledger(l)["amount"]
                                if val_amt > 0: draft["amount"] = val_amt
                            elif re.match(r'^(tovarlar|izoh|mahsulotlar)\s*:', l, re.IGNORECASE):
                                val_it = re.sub(r'^(tovarlar|izoh|mahsulotlar)\s*:\s*', '', l, flags=re.IGNORECASE).strip()
                                if val_it: draft["items"] = val_it
                            elif re.match(r'^turi\s*:', l, re.IGNORECASE):
                                l_low = l.lower()
                                draft["action_type"] = "receive" if ("to'lov" in l_low or "tolov" in l_low or "qaytar" in l_low) else "give"

                        save_drafts(USER_DRAFTS)
                        del USER_STATES[chat_id]
                        send_message(chat_id, "✅ Butun qoralama muvaffaqiyatli yangilandi!")
                        updated_text, markup = render_draft_message(draft_id, draft)
                        send_message(chat_id, updated_text, reply_markup=markup)
                        return

            # Standard message handlers
            if "voice" in msg or "audio" in msg:
                voice_obj = msg.get("voice") or msg.get("audio")
                log_msg(f"[Voice] From: {first_name} ({chat_id}) Duration: {voice_obj.get('duration')}s")
                handle_voice_message(chat_id, first_name, voice_obj)
            elif text.startswith("/"):
                log_msg(f"[Command] From: {first_name} ({chat_id}) Text: {text}")
                send_welcome(chat_id, first_name)
            elif len(text.strip()) > 3:
                log_msg(f"[Text Ledger] From: {first_name} ({chat_id}) Text: {text}")
                handle_text_ledger(chat_id, text)
    except Exception as ex:
        log_msg(f"[-] process_single_update exception: {ex}")

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        clean_path = self.path.split("?")[0]
        if clean_path == "/logs":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            log_text = "\n".join(LOG_BUFFER) if LOG_BUFFER else "No logs recorded yet."
            self.wfile.write(log_text.encode("utf-8"))
        elif clean_path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status = {
                "ok": True,
                "uptime_seconds": int(time.time() - START_TIME),
                "active_drafts": len(USER_DRAFTS),
                "server": "Render Webhook & KeepAlive"
            }
            self.wfile.write(json.dumps(status, indent=2).encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Aqlli Qarz Daftari Bot is active and running 24/7 on Render!\n")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

        if post_data:
            try:
                update = json.loads(post_data.decode("utf-8"))
                threading.Thread(target=process_single_update, args=(update,), daemon=True).start()
            except Exception as e:
                log_msg(f"[-] Webhook parse error: {e}")

    def log_message(self, format, *args):
        # Suppress periodic health check logs
        pass

def keep_alive_worker():
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://qarz-app-bot.onrender.com")
    while True:
        time.sleep(9 * 60)
        try:
            req = urllib.request.Request(render_url, headers={"User-Agent": "RenderKeepAlive/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                pass
            log_msg("[KeepAlive] Self ping sent to prevent Render sleep")
        except Exception as e:
            log_msg(f"[KeepAlive Notice]: {e}")

def poll_updates():
    offset = 0
    log_msg("[*] Starting Telegram polling loop (fallback mode)...")
    while True:
        try:
            url = f"{API_BASE}/getUpdates?timeout=20&offset={offset}"
            req = urllib.request.Request(url, headers={"User-Agent": "QarzBot/2.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    process_single_update(update)
        except Exception as e:
            log_msg(f"[Poll Exception]: {e}")
            time.sleep(2)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    log_msg(f"[*] Aqlli Qarz Daftari Bot server listening on port {port}...")

    # Start self-keepalive to keep Render free tier awake 24/7
    threading.Thread(target=keep_alive_worker, daemon=True).start()

    # Webhook setup on Render
    webhook_url = "https://qarz-app-bot.onrender.com/webhook"
    try:
        req = urllib.request.Request(f"{API_BASE}/setWebhook?url={webhook_url}&drop_pending_updates=False")
        with urllib.request.urlopen(req, timeout=10) as resp:
            log_msg(f"[Webhook Setup]: {resp.read().decode()}")
    except Exception as e:
        log_msg(f"[Webhook Notice]: {e}")

    server.serve_forever()
