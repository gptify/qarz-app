const BOT_TOKEN = process.env.BOT_TOKEN || "8994215084:AAGL0EkhqLFHIbpGd_Air9aGsW93KuHqFvA";
const WEBAPP_URL = "https://gptify.github.io/qarz-app/";
const AVATAR_URL = "https://raw.githubusercontent.com/gptify/qarz-app/main/qarz_bot_avatar.jpg";

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    return res.status(200).send("Qarz App Webhook is active 🚀");
  }

  try {
    const update = req.body;
    const message = update?.message;

    if (message && message.chat) {
      const chatId = message.chat.id;
      const firstName = message.from?.first_name || "Foydalanuvchi";
      const text = message.text || "";

      if (text.startsWith("/start") || text.startsWith("/app") || text.startsWith("/help")) {
        const caption = 
          `Assalomu alaykum, <b>${firstName}</b>! 🏪\n\n` +
          `<b>Aqlli Qarz Daftari (Mini App)</b>ga xush kelibsiz!\n\n` +
          `Ushbu ilova mahalla do'konlari uchun qarz va to'lovlarni ` +
          `Telegramdan chiqmasdan, 100% oson va shaffof yuritish imkonini beradi:\n\n` +
          `• 🎙 <b>Ovozli qarz yozish</b>\n` +
          `• 📱 <b>Katta tugmali POS kalkulyator</b>\n` +
          `• ↩️ <b>Xato kiritilsa 'Bekor qilish' (Undo)</b>\n` +
          `• 📲 <b>Odobli eslatmalar va Click/Payme havolalari</b>\n` +
          `• ☁️ <b>Bulutli zaxiralash</b>\n\n` +
          `Ilovani ochish uchun pastdagi <b>'🚀 Qarz Daftarini Ochish'</b> tugmasini bosing 👇`;

        const payload = {
          chat_id: chatId,
          photo: AVATAR_URL,
          caption: caption,
          parse_mode: "HTML",
          reply_markup: {
            inline_keyboard: [
              [
                {
                  text: "🚀 Qarz Daftarini Ochish (Mini App)",
                  web_app: { url: WEBAPP_URL }
                }
              ]
            ],
            keyboard: [
              [
                {
                  text: "📒 Qarz Daftarini Ochish",
                  web_app: { url: WEBAPP_URL }
                }
              ]
            ],
            resize_keyboard: true,
            is_persistent: true
          }
        };

        await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      }
    }

    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error("Webhook error:", err);
    return res.status(200).json({ ok: true, error: err.message });
  }
};
