# 📒 Qarz App — Aqlli Qarz Daftari (Telegram Mini App)

O‘zbekistondagi kichik va o‘rta savdo do‘konlari (*"Mahalla oziq-ovqat, xo‘jalik mollari, kiyim do‘konlari"*) uchun an’anaviy qog‘oz qarz daftarlarini to‘liq raqamlashtiruvchi zamonaviy **Telegram Mini App (TMA)**.

---

## 📱 Asosiy imkoniyatlar

1. **Tezkor Nasiya Yozish (3 soniya):**
   - Do‘kondor navbat paytida shoshilmasdan 3 ta tugmada qarz yozishi mumkin.
   - Tezkor summa tugmalari: `+10 ming`, `+20 ming`, `+50 ming`, `+100 ming`, `+500 ming`.
   - Tayyor tovar teglari: *Non, Yog‘, Go‘sht, Shakar, Sut, Tuxum, Sigaret, Ichimlik...*
2. **O‘zbekcha Ovozli Kiritish (Voice-to-Ledger):**
   - *"Anvar akaga 40 ming yog' va shakar"* deb aytilsa, ilova buni tushunadi va kerakli kataklarga to‘ldiradi.
3. **Mijoz Profili & Nasiya Limiti:**
   - Har bir mijozga ishonch chegarasi (limit) qo‘yish (masalan 400 000 so‘m).
   - Limitdan oshganda yoki to‘lov kechikkanida avtomatik sariq/qizil ogohlantirish.
4. **Odobli Eslatmalar Generatori:**
   - O‘zbekona xijolat bo‘lmaslik madaniyatiga mos 4 xil ohang:
     - 🤝 **Hurmatli / Odobli**
     - 😊 **Do‘stona**
     - 🕌 **Juma muborak**
     - 📄 **Rasmiy**
   - 1 ta tugma bilan Telegram yoki SMS orqali yuborish.
5. **Click / Payme To‘lov Havolasi:**
   - Eslatma ichida avtomatik Click va Payme to‘lov havolasi yuboriladi. Xaridor havolani bosib, darhol o‘z kartasidan do‘konga to‘lay oladi.
6. **Ta’minotchilar (Postavshiklar) Bo‘limi:**
   - Do‘kondorning o‘zi distribyutorlardan (Coca-Cola, nonvoyxona, go‘sht ta'minotchilari) olgan qarzlarini alohida tabda yuritadi.
7. **100% Oflayn va Xavfsiz:**
   - Barcha ma'lumotlar qurilmaning o‘zida (`localStorage`) saqlanadi, internet yo‘q paytda ham ishlaydi.
   - JSON va matnli hisobot eksporti mavjud.

---

## 🚀 Qanday ishga tushiriladi?

### 1. Lokal kompyuterda ochish:
Ikkita usul bor:
- `run_app.bat` faylini ikki marta bosing.
- Yoki terminalda:
  ```powershell
  python serve_tma.py
  ```
Brauzerda oching: [http://localhost:8085](http://localhost:8085)

### 2. Telegram Botga ulash (Mini App qilish):
1. **Telegram oching** va [@BotFather](https://t.me/BotFather) botiga kiring.
2. Yangi bot oching: `/newbot` (masalan: `QarzDaftarBot`).
3. Mini App yarating: `/newapp` buyrug‘ini yuboring.
4. Botni tanlang va Mini App nomini yozing.
5. URL so‘raganda, lokal sinov uchun **ngrok** yoki **cloudflared** havolasini bering:
   ```bash
   cloudflared tunnel --url http://localhost:8085
   ```
   *Yoki loyihani bepul Vercel / GitHub Pages'ga joylashtirib, o‘sha `https://...` manzilni kiriting.*
6. Tayyor! Bot menyusida yoki to‘g‘ridan-to‘g‘ri havolada Mini App ochiladi.

---

## 📁 Fayllar tuzilishi

```
tma_qarz/
├── index.html         # Asosiy mobil TMA interfeysi
├── css/
│   └── app.css        # Telegram UI mavzulariga mos responsive CSS
├── js/
│   ├── mock_data.js   # Mahalla do'koni uchun demo ma'lumotlar
│   ├── store.js       # Mahalliy baza va hisob-kitoblar (State)
│   ├── voice.js       # O'zbekcha ovozni aniqlash va tahlil qilish
│   ├── reminders.js   # Telegram xabar va Click/Payme generatori
│   └── app.js         # Boshqaruvchi asosiy script
├── serve_tma.py       # Lokal server
└── run_app.bat        # 1-klikda ishga tushirish
```
