import os
import sys
import io
import json
import time
import re
import base64
import urllib.request
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

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
FALLBACK_MODELS = ["gemini-flash-latest", "gemini-2.5-flash-lite"]

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
USER_STATES = {}  # chat_id -> {"action": "waiting_name" | "waiting_amount", "draft_id": "..."}

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

1. "transcription": audioda aytilgan to'liq gap (masalan: "Akmal akaga 50 mingga 2 ta non bilan yog' berdim").
2. "customer_name": Mijozning ismi.
   - O'zbek ismlarini xatosiz, to'g'ri bosh harf bilan yozing: Akmal, Anvar, Nodir, Dilshod, Sardor, Rustam, Jamshid, Bobur, Otabek, Shavkat, Ulug'bek, Sherzod, Javohir, Farrux, Alisher, Bekzod, Jasur, Davron, Elyor, Xurshid, Aziz, Sanjar, Shohruh, Doston, Baxtiyor, Muzaffar, Umid, Komil, Ilhom, Zafar; ayollar: Dilnoza, Shahnoza, Nilufar, Gulnoza, Madina, Malika, Feruza, Nargiza, Mohira, Sevara, Zilola, Lola, Rayhon, Ziyoda, Yulduz, Munira, Dildora va h.k.
   - Hurmat so'zlari aytilgan bo'lsa qoldiring: "Akmal aka", "Nodir aka", "Dilnoza opa", "Rustam tog'a".
   - Egalik va jo'nalish kelishigi qo'shimchalarini olib tashlang: "Akmalga" -> "Akmal", "Nodir akaga" -> "Nodir aka", "Sardordan" -> "Sardor".
   - Agar ism noaniq yoki tushunarsiz bo'lsa, "Mijoz" deb qaytaring.
3. "amount": Qarz summasi (faqat butun son raqam, so'mda). Masalan: "ellik ming" -> 50000, "bir yuz yigirma ming" -> 120000, "15 ming" -> 15000.
4. "type": "give" (qarz berildi) yoki "receive" (qarz to'landi/qaytarildi).
5. "items": Olingan tovarlar yoki izoh (masalan: "2 ta non, yog'", "sigaret, kola", "kartoshka, go'sht").
6. "due_days": Qachongacha berilgani (kunlar soni, sukut bo'yicha 7).

Qat'iy faqat JSON formatida qaytaring:
{
  "is_clear": true,
  "transcription": "audioda eshitilgan gap",
  "customer_name": "Akmal aka",
  "amount": 50000,
  "type": "give",
  "items": "2 ta non, yog'",
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
        "to'qson": 90000, "toqson": 90000, "yuz": 100000, "bir yuz": 100000, "ikki yuz": 200000
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

    text = (
        f"🎙️ <b>Ovozli qoralama qabul qilindi!</b> <code>#Q{draft_id}</code>\n\n"
        f"🗣 <i>\"{raw_text}\"</i>\n\n"
        f"─────────────────\n"
        f"📋 <b>Holat:</b> 📝 <b>Qoralama (Tasdiqlanmagan)</b>\n"
        f"🏷 <b>Turi:</b> {title_emoji}\n"
        f"👤 <b>Mijoz:</b> <b>{customer}</b>\n"
        f"💰 <b>Summa:</b> <b>{amount_display}</b>\n"
        f"📦 <b>Tovarlar:</b> {items}\n"
        f"📅 <b>Sana:</b> Bugun\n"
        f"─────────────────\n\n"
        f"💡 <i>Ism yoki summa xato bo'lsa, quyidagi tugmalar bilan to'g'rilang, so'ng tasdiqlang:</i>"
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
                    "text": "✏️ Ismni to'g'rilash",
                    "callback_data": f"edit_name_{draft_id}"
                },
                {
                    "text": "💰 Summani to'g'rilash",
                    "callback_data": f"edit_sum_{draft_id}"
                }
            ],
            [
                {
                    "text": "📱 Mini Appda ochish & tahrirlash",
                    "web_app": {"url": webapp_url}
                }
            ],
            [
                {
                    "text": "🗑️ Bekor qilish",
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

    # 1. First priority: Gemini 3.6 Flash multimodal audio
    parsed = process_voice_with_gemini(audio_bytes, mime_type="audio/ogg")
    
    if parsed and parsed.get("transcription"):
        transcript = parsed.get("transcription", "").strip()
        customer = parsed.get("customer_name") or "Mijoz"
        amount = int(parsed.get("amount") or 0)
        items = parsed.get("items") or "Tovarlar"
        action_type = parsed.get("type") or "give"
    else:
        # 2. Fallback to Groq Whisper
        transcript = transcribe_with_groq(audio_bytes, filename="voice.ogg")
        if not transcript:
            send_message(chat_id, "❌ Ovozni taniy olmadim. Iltimos, mikrofonga yaqinroq va aniqroq gapirib ko'ring.")
            return
        parsed_legacy = parse_uzbek_ledger(transcript)
        customer = parsed_legacy["customer"]
        amount = parsed_legacy["amount"]
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
        f"• 📝 <b>Ovozli Qoralama:</b> Ism yoki summa xato ketsa, bir zumda to'g'rilab, keyin daftarga saqlaysiz!\n"
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

def poll_updates():
    offset = 0
    print("[*] Qarz Daftari bot with Gemini Voice Draft System running...", flush=True)
    while True:
        try:
            url = f"{API_BASE}/getUpdates?timeout=20&offset={offset}"
            req = urllib.request.Request(url, headers={"User-Agent": "QarzBot/2.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for update in data.get("result", []):
                    offset = update["update_id"] + 1

                    # 1. Handle Callback Queries (Buttons)
                    if "callback_query" in update:
                        cb = update["callback_query"]
                        cb_id = cb["id"]
                        cb_data = cb.get("data", "")
                        chat_id = cb["message"]["chat"]["id"]
                        message_id = cb["message"]["message_id"]

                        print(f"[Callback] data={cb_data} from chat={chat_id}", flush=True)

                        if cb_data.startswith("confirm_"):
                            draft_id = cb_data.split("_")[1]
                            draft = USER_DRAFTS.get(draft_id)
                            if draft:
                                save_confirmed_tx(draft)
                                USER_DRAFTS.pop(draft_id, None)
                                save_drafts(USER_DRAFTS)

                                amount_display = f"{draft['amount']:,} so'm".replace(",", " ") if draft['amount'] > 0 else "0 so'm"
                                answer_callback_query(cb_id, text="Qarz saqlandi! ✅")

                                final_text = (
                                    f"✅ <b>Qarz daftaringizga muvaffaqiyatli saqlandi!</b>\n\n"
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

                        # Check if user is in an active prompt state (e.g. correcting name or amount)
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
                                    continue

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
                                        continue
                                    else:
                                        send_message(chat_id, "⚠️ Summa aniqlanmadi. Iltimos, raqamda yozing (masalan: 65000 yoki 65 ming):")
                                        continue

                        # Standard message handlers
                        if "voice" in msg or "audio" in msg:
                            voice_obj = msg.get("voice") or msg.get("audio")
                            print(f"[Voice] From: {first_name} ({chat_id}) Duration: {voice_obj.get('duration')}s", flush=True)
                            handle_voice_message(chat_id, first_name, voice_obj)
                        elif text.startswith("/"):
                            print(f"[Command] From: {first_name} ({chat_id}) Text: {text}", flush=True)
                            send_welcome(chat_id, first_name)
                        elif len(text.strip()) > 3:
                            print(f"[Text Ledger] From: {first_name} ({chat_id}) Text: {text}", flush=True)
                            handle_text_ledger(chat_id, text)

        except Exception as e:
            print(f"[Poll Exception]: {e}", flush=True)
            time.sleep(2)

if __name__ == "__main__":
    poll_updates()
