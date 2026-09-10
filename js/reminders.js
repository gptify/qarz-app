// Reminder & Payment Link Generator for Qarz App TMA
class ReminderService {
  constructor() {
    this.shopName = "Mahalla Baraka Do'koni";
    // Demo merchant card or Click/Payme link
    this.merchantCard = "8600 **** **** 4512";
  }

  formatMoney(amount) {
    return new Intl.NumberFormat('uz-UZ').format(amount) + " so'm";
  }

  generatePaymentLink(amount) {
    // Payme P2P or Click web link format
    const encodedCard = encodeURIComponent("8600123456784512");
    return `https://payme.uz/fallback/pay?amount=${amount * 100}`;
  }

  generateReminderText(customer, tone = "polite") {
    const formattedDebt = this.formatMoney(customer.totalDebt);
    const shop = window.store?.state?.shopName || this.shopName;
    const payLink = this.generatePaymentLink(customer.totalDebt);

    switch (tone) {
      case "friendly":
        return `Assalomu alaykum ${customer.name}! 
Siz bilan do'konda ko'rishganimizdan doim xursandmiz. 
"${shop}"dagi joriy nasiya hisobingiz: ${formattedDebt}.
Imkoningiz bo'lganda kirib o'tsangiz minnatdor bo'lardik. Rahmat!`;

      case "juma":
        return `Assalomu alaykum ${customer.name}! 
Juma ayyomingiz muborak bo'lsin, oilangizga qut-baraka tilaymiz!
"${shop}"dagi o'zaro hisob-kitob bo'yicha qoldiq: ${formattedDebt}.
To'lovni do'konga kelib yoki Payme/Click orqali amalga oshirishingiz mumkin. Kuningiz xayrli o'tsin!`;

      case "formal":
        return `Hurmatli ${customer.name}!
"${shop}" do'koni hisob-kitob bo'limidan eslatma:
Sizning nasiya savdo bo'yicha qarz qoldig'ingiz: ${formattedDebt}.
Iltimos, belgilangan qarz muddatiga rioya qilgan holda to'lovni yaqin kunlarda so'ndirishingizni so'raymiz.
Plastik karta: 8600 1234 5678 4512`;

      case "polite":
      default:
        return `Assalomu alaykum, hurmatli ${customer.name}!
"${shop}" do'konidan xabar qilmoqdamiz. 
Sizning jami nasiya balansingiz: ${formattedDebt}.
To'lov uchun karta: 8600 1234 5678 4512
Yoki tezkor to'lov havolasi: ${payLink}
Sog'-salomat bo'ling!`;
    }
  }

  shareViaTelegram(customer, tone = "polite") {
    const text = this.generateReminderText(customer, tone);
    const encodedText = encodeURIComponent(text);

    // If customer has a telegram username, we can suggest direct chat
    if (customer.telegramUsername) {
      const username = customer.telegramUsername.replace("@", "");
      // Open direct chat or share
      window.open(`https://t.me/${username}?text=${encodedText}`, "_blank");
    } else {
      // General share
      window.open(`https://t.me/share/url?url=&text=${encodedText}`, "_blank");
    }
  }

  shareViaSMS(customer, tone = "polite") {
    const text = this.generateReminderText(customer, tone);
    const phone = customer.phone ? customer.phone.replace(/\s+/g, '') : '';
    window.location.href = `sms:${phone}?body=${encodeURIComponent(text)}`;
  }

  generateConfirmationReceipt(customer, transaction) {
    const shop = window.store?.state?.shopName || this.shopName;
    const isDebt = transaction.type === "debt";
    const amountStr = this.formatMoney(transaction.amount);
    const balanceStr = this.formatMoney(customer.totalDebt);
    const payLink = this.generatePaymentLink(customer.totalDebt);
    const dueDateStr = transaction.dueDate ? `\n⏳ To'lov muddati: ${transaction.dueDate} gacha` : '';

    if (isDebt) {
      return `🧾 YANGI NASIYA XARIDI CHEKI
Do'kon: "${shop}"
Mijoz: ${customer.name}
Sana: ${transaction.date}
-----------------------------
📦 Tovarlar: ${transaction.note || 'Nasiya savdo'}
💰 Xarid summasi: +${amountStr}${dueDateStr}
-----------------------------
📊 Joriy qarz balansingiz: ${balanceStr}

Plastik karta: 8600 1234 5678 4512
Tezkor to'lov (Payme/Click): ${payLink}
Xaridingiz uchun rahmat!`;
    } else {
      return `🧾 QARZ SO'NDIRILDI (TO'LOV CHEKI)
Do'kon: "${shop}"
Mijoz: ${customer.name}
Sana: ${transaction.date}
-----------------------------
💵 Qabul qilingan to'lov: -${amountStr} (${transaction.note || 'To\'lov'})
-----------------------------
📊 Qolgan qarz balansingiz: ${balanceStr}

Hisob-kitob uchun rahmat, sog'-salomat bo'ling!`;
    }
  }

  shareReceiptViaTelegram(customer, transaction) {
    const text = this.generateConfirmationReceipt(customer, transaction);
    const encoded = encodeURIComponent(text);
    if (customer.telegramUsername) {
      const username = customer.telegramUsername.replace("@", "");
      window.open(`https://t.me/${username}?text=${encoded}`, "_blank");
    } else {
      window.open(`https://t.me/share/url?url=&text=${encoded}`, "_blank");
    }
  }

  shareReceiptViaSMS(customer, transaction) {
    const text = this.generateConfirmationReceipt(customer, transaction);
    const phone = customer.phone ? customer.phone.replace(/\s+/g, '') : '';
    window.location.href = `sms:${phone}?body=${encodeURIComponent(text)}`;
  }

  copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    } else {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      textArea.style.opacity = "0";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        document.execCommand('copy');
      } catch (err) {
        console.error('Copy failed', err);
      }
      document.body.removeChild(textArea);
      return Promise.resolve();
    }
  }
}

window.reminders = new ReminderService();
