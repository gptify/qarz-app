// State management and storage layer for Qarz App
function getStorageKey() {
  try {
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    if (tgUser && tgUser.id) {
      return `qarz_app_tma_user_${tgUser.id}`;
    }
  } catch (e) {}
  return "qarz_app_tma_v1";
}

class QarzStore {
  constructor() {
    this.storageKey = getStorageKey();
    this.state = this.load();
    this.listeners = [];
  }

  load() {
    let data = null;
    try {
      const saved = localStorage.getItem(this.storageKey);
      if (saved) {
        data = JSON.parse(saved);
      } else {
        // Check fallback legacy key
        const legacy = localStorage.getItem("qarz_app_tma_v1");
        if (legacy) {
          data = JSON.parse(legacy);
        }
      }
    } catch (e) {
      console.warn("Could not read from localStorage, loading initial mock data", e);
    }
    if (!data) {
      data = JSON.parse(JSON.stringify(window.INITIAL_DATA || {}));
      const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
      if (tgUser && tgUser.first_name) {
        data.shopName = `${tgUser.first_name} do'koni`;
      }
    }
    return data;
  }

  updateShopInfo({ shopName, ownerPhone, merchantCard }) {
    if (shopName) this.state.shopName = shopName.trim();
    if (ownerPhone !== undefined) this.state.ownerPhone = ownerPhone.trim();
    if (merchantCard !== undefined) this.state.merchantCard = merchantCard.trim();
    this.save();
  }

  save() {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.state));
    } catch (e) {
      console.error("Failed to save to localStorage", e);
    }
    this.notify();
  }

  resetToDemo() {
    this.state = JSON.parse(JSON.stringify(window.INITIAL_DATA || {}));
    this.save();
  }

  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  notify() {
    this.listeners.forEach(fn => fn(this.state));
  }

  // --- Calculations ---
  getTotalCustomerDebt() {
    return this.state.customers.reduce((sum, c) => sum + (c.totalDebt || 0), 0);
  }

  getTotalSupplierDebt() {
    return this.state.suppliers.reduce((sum, s) => sum + (s.totalDebt || 0), 0);
  }

  getTodayStats() {
    const todayStr = new Date().toISOString().slice(0, 10);
    let todayGiven = 0;
    let todayCollected = 0;

    this.state.customers.forEach(c => {
      (c.transactions || []).forEach(t => {
        if (t.date && t.date.startsWith(todayStr)) {
          if (t.type === "debt") todayGiven += t.amount;
          if (t.type === "payment") todayCollected += t.amount;
        }
      });
    });

    return { todayGiven, todayCollected };
  }

  // --- Customer Operations ---
  getCustomers(filter = "all", searchQuery = "") {
    let list = [...(this.state.customers || [])];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(c => 
        c.name.toLowerCase().includes(q) || 
        c.phone.toLowerCase().includes(q) ||
        (c.telegramUsername && c.telegramUsername.toLowerCase().includes(q))
      );
    }

    if (filter === "overdue") {
      list = list.filter(c => c.status === "overdue" || (c.limit && c.totalDebt > c.limit));
    } else if (filter === "active") {
      list = list.filter(c => c.totalDebt > 0);
    } else if (filter === "settled") {
      list = list.filter(c => c.totalDebt === 0);
    }

    // Sort: highest debt first
    list.sort((a, b) => b.totalDebt - a.totalDebt);
    return list;
  }

  getCustomerById(id) {
    return this.state.customers.find(c => c.id === id);
  }

  findCustomerByName(name) {
    if (!name) return null;
    const q = name.trim().toLowerCase();
    return this.state.customers.find(c => 
      c.name.toLowerCase() === q || 
      c.name.toLowerCase().startsWith(q) ||
      c.name.toLowerCase().includes(q)
    );
  }

  addQuickProduct(tag) {
    if (!this.state.quickProducts) {
      this.state.quickProducts = [...(window.INITIAL_DATA.quickProducts || [])];
    }
    const clean = tag.trim();
    if (clean && !this.state.quickProducts.includes(clean)) {
      this.state.quickProducts.push(clean);
      this.save();
    }
  }

  removeQuickProduct(tag) {
    if (!this.state.quickProducts) {
      this.state.quickProducts = [...(window.INITIAL_DATA.quickProducts || [])];
    }
    this.state.quickProducts = this.state.quickProducts.filter(t => t !== tag);
    this.save();
  }

  addCustomer({ name, phone, telegramUsername, limit }) {
    const newCust = {
      id: "c_" + Date.now(),
      name: name.trim(),
      phone: phone ? phone.trim() : "",
      telegramUsername: telegramUsername ? telegramUsername.replace("@", "").trim() : "",
      limit: Number(limit) || 500000,
      totalDebt: 0,
      lastTransactionDate: new Date().toISOString().slice(0, 10),
      status: "settled",
      transactions: []
    };
    this.state.customers.unshift(newCust);
    this.save();
    return newCust;
  }

  addDebt({ customerId, amount, note, items = [], date, dueDate }) {
    let customer = this.getCustomerById(customerId);
    if (!customer) return null;

    const numAmount = Number(amount) || 0;
    const now = new Date();
    let recordDateStr = date ? date.replace("T", " ") : now.toISOString().slice(0, 16).replace("T", " ");

    const tx = {
      id: "t_" + Date.now(),
      type: "debt",
      amount: numAmount,
      date: recordDateStr,
      dueDate: dueDate || "",
      note: note || items.join(", ") || "Nasiya savdo",
      items: items
    };

    customer.transactions.unshift(tx);
    customer.totalDebt = (customer.totalDebt || 0) + numAmount;
    customer.lastTransactionDate = recordDateStr.slice(0, 10);
    customer.status = (customer.limit && customer.totalDebt > customer.limit) ? "overdue" : "active";

    this.save();
    return tx;
  }

  recordPayment({ customerId, amount, note = "To'lov qabul qilindi", date }) {
    let customer = this.getCustomerById(customerId);
    if (!customer) return null;

    const numAmount = Math.min(Number(amount) || 0, customer.totalDebt);
    const now = new Date();
    let recordDateStr = date ? date.replace("T", " ") : now.toISOString().slice(0, 16).replace("T", " ");

    const tx = {
      id: "t_" + Date.now(),
      type: "payment",
      amount: numAmount,
      date: recordDateStr,
      note: note,
      items: []
    };

    customer.transactions.unshift(tx);
    customer.totalDebt = Math.max(0, (customer.totalDebt || 0) - numAmount);
    customer.lastTransactionDate = recordDateStr.slice(0, 10);
    customer.status = customer.totalDebt === 0 ? "settled" : "active";

    this.save();
    return tx;
  }

  // --- Supplier Operations ---
  getSuppliers() {
    return this.state.suppliers || [];
  }

  addSupplier({ name, phone, note, initialDebt }) {
    const s = {
      id: "s_" + Date.now(),
      name: name.trim(),
      phone: phone || "",
      note: note || "",
      totalDebt: Number(initialDebt) || 0,
      lastDate: new Date().toISOString().slice(0, 10)
    };
    this.state.suppliers.unshift(s);
    this.save();
    return s;
  }

  updateSupplierPayment({ supplierId, amount }) {
    const s = this.state.suppliers.find(sup => sup.id === supplierId);
    if (!s) return;
    s.totalDebt = Math.max(0, (s.totalDebt || 0) - Number(amount));
    this.save();
  }

  // --- Undo & History Rollback ---
  undoTransaction(customerId, txId) {
    const customer = this.getCustomerById(customerId);
    if (!customer) return null;
    const txIndex = (customer.transactions || []).findIndex(t => t.id === txId);
    if (txIndex === -1) return null;

    const [removedTx] = customer.transactions.splice(txIndex, 1);

    // Recalculate debt accurately based on remaining transactions
    let recalculated = 0;
    // Iterate from oldest to newest
    const chronologic = [...customer.transactions].reverse();
    chronologic.forEach(t => {
      if (t.type === "debt") {
        recalculated += t.amount;
      } else if (t.type === "payment") {
        recalculated = Math.max(0, recalculated - t.amount);
      }
    });

    customer.totalDebt = recalculated;
    customer.status = (customer.limit && customer.totalDebt > customer.limit)
      ? "overdue"
      : (customer.totalDebt > 0 ? "active" : "settled");

    if (customer.transactions.length > 0) {
      customer.lastTransactionDate = (customer.transactions[0].date || "").slice(0, 10);
    }

    this.save();
    return removedTx;
  }

  // --- Backup & Cloud Sync Utilities ---
  exportDataJSON() {
    return JSON.stringify({
      ...this.state,
      exportedAt: new Date().toISOString(),
      appVersion: "1.2.0"
    }, null, 2);
  }

  importDataJSON(jsonStr) {
    try {
      const data = JSON.parse(jsonStr);
      if (!data.customers || !Array.isArray(data.customers)) {
        return { success: false, error: "Noto'g'ri fayl: 'customers' ro'yxati mavjud emas." };
      }
      this.state = data;
      this.save();
      return { success: true, customerCount: data.customers.length };
    } catch (e) {
      return { success: false, error: e.message };
    }
  }
}

window.store = new QarzStore();
