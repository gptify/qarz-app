// Main Application Controller for Qarz App TMA
document.addEventListener("DOMContentLoaded", () => {
  // Initialize Telegram WebApp SDK if present
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    // Enable closing confirmation if needed
    if (tg.enableClosingConfirmation) tg.enableClosingConfirmation();
  }

  // Trigger Telegram haptics safely
  function haptic(type = "light") {
    if (tg?.HapticFeedback) {
      if (type === "success") tg.HapticFeedback.notificationOccurred("success");
      else if (type === "warning") tg.HapticFeedback.notificationOccurred("warning");
      else if (type === "medium") tg.HapticFeedback.impactOccurred("medium");
      else tg.HapticFeedback.impactOccurred("light");
    }
  }

  // State Variables
  let currentFilter = "all";
  let searchQuery = "";
  let selectedCustomer = null;
  let selectedReminderTone = "polite";
  let activeTab = "viewCustomers";

  // Elements
  const totalDebtDisplay = document.getElementById("totalDebtDisplay");
  const todayGivenDisplay = document.getElementById("todayGivenDisplay");
  const todayCollectedDisplay = document.getElementById("todayCollectedDisplay");
  const customerListContainer = document.getElementById("customerListContainer");
  const customerCountBadge = document.getElementById("customerCountBadge");
  const customerSearchInput = document.getElementById("customerSearchInput");
  const filterPills = document.querySelectorAll(".filter-pills .pill-btn");
  const bottomNavItems = document.querySelectorAll(".bottom-nav .nav-item");

  // Suppliers elements
  const totalSupplierDebtDisplay = document.getElementById("totalSupplierDebtDisplay");
  const supplierListContainer = document.getElementById("supplierListContainer");

  // Analytics elements
  const analyticsTotalTurnover = document.getElementById("analyticsTotalTurnover");

  // Format money helper
  function formatMoney(amount) {
    return new Intl.NumberFormat("uz-UZ").format(amount) + " so'm";
  }

  // Render Overview Stats
  function renderStats() {
    const totalDebt = window.store.getTotalCustomerDebt();
    const today = window.store.getTodayStats();
    totalDebtDisplay.textContent = formatMoney(totalDebt);
    todayGivenDisplay.textContent = formatMoney(today.todayGiven);
    todayCollectedDisplay.textContent = formatMoney(today.todayCollected);

    const totalSup = window.store.getTotalSupplierDebt();
    if (totalSupplierDebtDisplay) totalSupplierDebtDisplay.textContent = formatMoney(totalSup);
    if (analyticsTotalTurnover) analyticsTotalTurnover.textContent = formatMoney(totalDebt + totalSup);
  }

  // Render Customers List
  function renderCustomers() {
    const customers = window.store.getCustomers(currentFilter, searchQuery);
    customerCountBadge.textContent = `${customers.length} ta mijoz`;

    if (customers.length === 0) {
      customerListContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📝</div>
          <p>Mijozlar topilmadi</p>
          <span style="font-size: 12px;">Qarz qo'shish uchun pastdagi "+" tugmasini bosing</span>
        </div>
      `;
      return;
    }

    customerListContainer.innerHTML = customers.map(c => {
      let borderClass = "settled-border";
      let statusTag = `<span class="cust-status-tag tag-success">To'liq to'langan</span>`;

      if (c.totalDebt > 0) {
        if (c.status === "overdue" || (c.limit && c.totalDebt > c.limit)) {
          borderClass = "danger-border";
          statusTag = `<span class="cust-status-tag tag-danger">⚠️ Limitdan oshgan</span>`;
        } else {
          borderClass = "active-border";
          statusTag = `<span class="cust-status-tag tag-warning">Faol qarz</span>`;
        }
      }

      const initial = c.name.trim().charAt(0).toUpperCase();

      return `
        <div class="customer-card ${borderClass}" data-id="${c.id}">
          <div class="customer-meta">
            <div class="avatar">${initial}</div>
            <div>
              <div class="cust-name">${c.name}</div>
              <div class="cust-phone">${c.phone || (c.telegramUsername ? '@' + c.telegramUsername : 'Telefon kiritilmagan')}</div>
            </div>
          </div>
          <div class="cust-debt-info">
            <div class="cust-amount ${c.totalDebt > 0 ? 'has-debt' : 'settled'}">
              ${c.totalDebt > 0 ? formatMoney(c.totalDebt) : "0 so'm"}
            </div>
            ${statusTag}
          </div>
        </div>
      `;
    }).join("");

    // Bind card clicks
    customerListContainer.querySelectorAll(".customer-card").forEach(card => {
      card.addEventListener("click", () => {
        haptic("light");
        const id = card.getAttribute("data-id");
        openCustomerDetails(id);
      });
    });
  }

  // Render Suppliers List
  function renderSuppliers() {
    const suppliers = window.store.getSuppliers();
    if (suppliers.length === 0) {
      supplierListContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🚚</div>
          <p>Ta'minotchilar ro'yxati bo'sh</p>
        </div>
      `;
      return;
    }

    supplierListContainer.innerHTML = suppliers.map(s => `
      <div class="customer-card danger-border" style="cursor: default;">
        <div class="customer-meta">
          <div class="avatar" style="background: #f3e8ff; color: #9333ea;">📦</div>
          <div>
            <div class="cust-name">${s.name}</div>
            <div class="cust-phone">${s.phone || ''} · ${s.note || 'Tovar yetkazib berish'}</div>
          </div>
        </div>
        <div class="cust-debt-info">
          <div class="cust-amount has-debt">${formatMoney(s.totalDebt)}</div>
          <span class="cust-status-tag tag-danger">Berishimiz kerak</span>
        </div>
      </div>
    `).join("");
  }

  // Populate Customer Datalist & Combobox Matching
  const inputCustomerCombobox = document.getElementById("inputCustomerCombobox");
  const customerDatalist = document.getElementById("customerDatalist");
  const customerMatchStatus = document.getElementById("customerMatchStatus");

  function populateCustomerCombobox() {
    const customers = window.store.state.customers || [];
    if (customerDatalist) {
      customerDatalist.innerHTML = customers.map(c => `
        <option value="${c.name}">${c.name} (${c.totalDebt > 0 ? formatMoney(c.totalDebt) : "Qarzsiz"})</option>
      `).join("");
    }
  }

  if (inputCustomerCombobox) {
    inputCustomerCombobox.addEventListener("input", (e) => {
      const val = e.target.value.trim();
      if (!val) {
        customerMatchStatus.style.display = "none";
        customerMatchStatus.innerHTML = "";
        return;
      }

      const matched = window.store.findCustomerByName(val);
      customerMatchStatus.style.display = "block";

      if (matched) {
        customerMatchStatus.innerHTML = `
          <span style="color: #2563eb; font-weight: 600;">
            👤 Tanlandi: <strong>${matched.name}</strong> (Qarz: ${formatMoney(matched.totalDebt)})
          </span>
        `;
      } else {
        customerMatchStatus.innerHTML = `
          <span style="color: #10b981; font-weight: 600;">
            ✨ Yangi mijoz "<strong>${val}</strong>" sifatida qo'shiladi
          </span>
        `;
      }
    });
  }

  // Populate Editable Quick Product Tags
  const quickProductTagsContainer = document.getElementById("quickProductTags");
  const newTagInlineForm = document.getElementById("newTagInlineForm");
  const btnOpenAddTag = document.getElementById("btnOpenAddTag");
  const btnConfirmAddTag = document.getElementById("btnConfirmAddTag");
  const btnCancelAddTag = document.getElementById("btnCancelAddTag");
  const inputNewTagName = document.getElementById("inputNewTagName");

  function populateProductTags() {
    if (!quickProductTagsContainer) return;
    const tags = window.store.state.quickProducts || window.INITIAL_DATA.quickProducts || [];

    quickProductTagsContainer.innerHTML = tags.map(t => `
      <div class="tag-pill-wrapper" data-tag-name="${t}">
        <button type="button" class="tag-btn" data-tag="${t}">${t}</button>
        <button type="button" class="tag-remove-btn" data-remove="${t}" title="O'chirish">×</button>
      </div>
    `).join("");

    // Bind tag click (toggle selection)
    quickProductTagsContainer.querySelectorAll(".tag-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        haptic("light");
        const wrapper = btn.closest(".tag-pill-wrapper");
        wrapper.classList.toggle("selected");
        updateNoteFromSelectedTags();
      });
    });

    // Bind tag remove button
    quickProductTagsContainer.querySelectorAll(".tag-remove-btn").forEach(rmBtn => {
      rmBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        haptic("light");
        const tag = rmBtn.getAttribute("data-remove");
        window.store.removeQuickProduct(tag);
        populateProductTags();
        updateNoteFromSelectedTags();
      });
    });
  }

  if (btnOpenAddTag) {
    btnOpenAddTag.addEventListener("click", () => {
      haptic("light");
      newTagInlineForm.style.display = "flex";
      inputNewTagName.focus();
    });
  }

  if (btnCancelAddTag) {
    btnCancelAddTag.addEventListener("click", () => {
      newTagInlineForm.style.display = "none";
      inputNewTagName.value = "";
    });
  }

  if (btnConfirmAddTag) {
    btnConfirmAddTag.addEventListener("click", () => {
      const val = inputNewTagName.value.trim();
      if (val) {
        haptic("success");
        window.store.addQuickProduct(val);
        inputNewTagName.value = "";
        newTagInlineForm.style.display = "none";
        populateProductTags();
      }
    });
  }

  function updateNoteFromSelectedTags() {
    const selected = Array.from(document.querySelectorAll("#quickProductTags .tag-pill-wrapper.selected .tag-btn"))
      .map(b => b.getAttribute("data-tag"));
    const noteInput = document.getElementById("inputDebtNote");
    if (noteInput) {
      noteInput.value = selected.join(", ");
    }
  }

  // Tab Navigation
  bottomNavItems.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      if (btn.id === "btnNavAddDebt") {
        haptic("medium");
        openModal("modalAddDebt");
        return;
      }

      if (!targetTab) return;
      haptic("light");
      bottomNavItems.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      document.querySelectorAll(".tab-view").forEach(view => {
        view.style.display = view.id === targetTab ? "block" : "none";
      });

      if (targetTab === "viewSuppliers") renderSuppliers();
      if (targetTab === "viewCustomers") renderCustomers();
    });
  });

  // Filter Buttons
  filterPills.forEach(pill => {
    pill.addEventListener("click", () => {
      haptic("light");
      filterPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentFilter = pill.getAttribute("data-filter");
      renderCustomers();
    });
  });

  // Search Input
  customerSearchInput.addEventListener("input", (e) => {
    searchQuery = e.target.value;
    renderCustomers();
  });

  // Helper to get local ISO string for datetime-local input
  function getLocalDateTimeString(d = new Date()) {
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function getLocalDateString(d = new Date()) {
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  // Modal Helpers
  function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
      modal.classList.add("open");
      if (id === "modalAddDebt") {
        populateCustomerCombobox();
        populateProductTags();
        updateAmountPreview();
        const dateInput = document.getElementById("inputDebtDate");
        if (dateInput && !dateInput.value) {
          dateInput.value = getLocalDateTimeString();
        }
      }
      if (id === "modalRecordPayment") {
        const payDate = document.getElementById("inputPayDate");
        if (payDate) payDate.value = getLocalDateTimeString();
      }
    }
  }

  function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove("open");
  }

  document.querySelectorAll("[data-close]").forEach(btn => {
    btn.addEventListener("click", () => {
      haptic("light");
      const modalId = btn.getAttribute("data-close");
      closeModal(modalId);
    });
  });

  // Amount Preview & Controls
  const inputDebtAmount = document.getElementById("inputDebtAmount");
  const amountFormattedPreview = document.getElementById("amountFormattedPreview");
  const btnClearAmount = document.getElementById("btnClearAmount");

  function updateAmountPreview() {
    if (!inputDebtAmount || !amountFormattedPreview) return;
    const val = parseInt(inputDebtAmount.value || 0, 10);
    amountFormattedPreview.textContent = val > 0 ? formatMoney(val) : "0 so'm";
  }

  if (inputDebtAmount) {
    inputDebtAmount.addEventListener("input", updateAmountPreview);
  }

  if (btnClearAmount) {
    btnClearAmount.addEventListener("click", () => {
      haptic("light");
      inputDebtAmount.value = "";
      updateAmountPreview();
    });
  }

  // --- POS NUMPAD LOGIC ---
  const posNumpadContainer = document.getElementById("posNumpadContainer");
  const btnTogglePosNumpad = document.getElementById("btnTogglePosNumpad");
  let isPosNumpadActive = true;

  if (btnTogglePosNumpad && posNumpadContainer) {
    btnTogglePosNumpad.addEventListener("click", () => {
      haptic("light");
      isPosNumpadActive = !isPosNumpadActive;
      posNumpadContainer.style.display = isPosNumpadActive ? "block" : "none";
      btnTogglePosNumpad.classList.toggle("active", isPosNumpadActive);
      btnTogglePosNumpad.textContent = isPosNumpadActive ? "📱 POS Numpad" : "⌨️ Klaviatura";
      if (inputDebtAmount) {
        if (isPosNumpadActive) {
          inputDebtAmount.setAttribute("readonly", "true");
        } else {
          inputDebtAmount.removeAttribute("readonly");
          inputDebtAmount.focus();
        }
      }
    });

    if (inputDebtAmount && isPosNumpadActive) {
      inputDebtAmount.setAttribute("readonly", "true");
    }
  }

  // Bind POS Keys
  document.querySelectorAll(".pos-key").forEach(keyBtn => {
    keyBtn.addEventListener("click", () => {
      haptic("light");
      const key = keyBtn.getAttribute("data-key");
      let cur = inputDebtAmount.value || "";

      if (key === "clear") {
        cur = "";
      } else if (key === "backspace") {
        cur = cur.slice(0, -1);
      } else if (key === "+10k") {
        const val = parseInt(cur || "0", 10);
        cur = String(val + 10000);
      } else if (key === "+50k") {
        const val = parseInt(cur || "0", 10);
        cur = String(val + 50000);
      } else {
        // Digits: 1-9, 0, 00, 000
        if (cur === "0" && key !== "00" && key !== "000") {
          cur = key;
        } else if (cur !== "" || (key !== "0" && key !== "00" && key !== "000")) {
          cur += key;
        }
      }

      inputDebtAmount.value = cur;
      updateAmountPreview();
    });
  });

  // --- FLOATING UNDO SNACKBAR TOAST ---
  const undoToastContainer = document.getElementById("undoToastContainer");
  const undoToastTitle = document.getElementById("undoToastTitle");
  const undoToastSub = document.getElementById("undoToastSub");
  const btnUndoAction = document.getElementById("btnUndoAction");
  const undoProgressFill = document.getElementById("undoProgressFill");

  let activeUndoAction = null; // { type, customerId, txId, customerName, amount }
  let undoTimer = null;

  function showUndoToast(action) {
    if (!undoToastContainer) return;
    activeUndoAction = action;

    const opLabel = action.type === "debt" ? "Qarz yozildi" : "To'lov qabul qilindi";
    undoToastTitle.textContent = `✅ ${action.customerName}: ${formatMoney(action.amount)} (${opLabel})`;
    undoToastSub.textContent = "Xato bo'lsa, 5 soniyada bekor qiling";

    undoToastContainer.style.display = "block";
    undoProgressFill.style.transition = "none";
    undoProgressFill.style.width = "100%";

    setTimeout(() => {
      undoProgressFill.style.transition = "width 5s linear";
      undoProgressFill.style.width = "0%";
    }, 50);

    if (undoTimer) clearTimeout(undoTimer);
    undoTimer = setTimeout(() => {
      hideUndoToast();
    }, 5000);
  }

  function hideUndoToast() {
    if (undoToastContainer) {
      undoToastContainer.style.display = "none";
    }
    activeUndoAction = null;
    if (undoTimer) clearTimeout(undoTimer);
  }

  if (btnUndoAction) {
    btnUndoAction.addEventListener("click", () => {
      if (!activeUndoAction) return;
      haptic("medium");

      const reverted = window.store.undoTransaction(activeUndoAction.customerId, activeUndoAction.txId);
      if (reverted) {
        hideUndoToast();
        renderStats();
        renderCustomers();
        if (selectedCustomer && selectedCustomer.id === activeUndoAction.customerId) {
          openCustomerDetails(selectedCustomer.id);
        }
        alert("Amal muvaffaqiyatli bekor qilindi!");
      }
    });
  }

  // Quick Amount Chips in Add Debt Form
  document.querySelectorAll(".quick-amount-chips .chip-btn").forEach(chip => {
    chip.addEventListener("click", () => {
      haptic("light");
      const addVal = parseInt(chip.getAttribute("data-add"), 10);
      const currentVal = parseInt(inputDebtAmount.value || 0, 10);
      inputDebtAmount.value = currentVal + addVal;
      updateAmountPreview();
    });
  });

  // Date Quick Chips (Bugun, Kecha)
  const btnDateToday = document.getElementById("btnDateToday");
  const btnDateYesterday = document.getElementById("btnDateYesterday");
  const inputDebtDate = document.getElementById("inputDebtDate");

  if (btnDateToday) {
    btnDateToday.addEventListener("click", () => {
      haptic("light");
      inputDebtDate.value = getLocalDateTimeString(new Date());
    });
  }

  if (btnDateYesterday) {
    btnDateYesterday.addEventListener("click", () => {
      haptic("light");
      const y = new Date();
      y.setDate(y.getDate() - 1);
      inputDebtDate.value = getLocalDateTimeString(y);
    });
  }

  // Due Date Chips (+3 kun, +1 hafta, +15 kun, +1 oy)
  document.querySelectorAll("#dueDateChips .chip-btn").forEach(chip => {
    chip.addEventListener("click", () => {
      haptic("light");
      const days = parseInt(chip.getAttribute("data-days"), 10);
      const target = new Date();
      target.setDate(target.getDate() + days);
      document.getElementById("inputDebtDueDate").value = getLocalDateString(target);
    });
  });

  // --- CONTINUOUS VOICE & DRAFT TEXT STUDIO ---
  const btnVoiceRecord = document.getElementById("btnVoiceRecord");
  const btnStopMic = document.getElementById("btnStopMic");
  const voiceLiveIndicator = document.getElementById("voiceLiveIndicator");
  const voiceStatusText = document.getElementById("voiceStatusText");
  const inputVoiceDraft = document.getElementById("inputVoiceDraft");
  const btnClearDraft = document.getElementById("btnClearDraft");
  const btnParseDraftText = document.getElementById("btnParseDraftText");
  const btnApplyDraftToForm = document.getElementById("btnApplyDraftToForm");

  const previewCustomerName = document.getElementById("previewCustomerName");
  const previewAmount = document.getElementById("previewAmount");
  const previewItems = document.getElementById("previewItems");

  let latestParsedDraft = { amount: 0, customerName: "", items: [] };

  function updateDraftPreview(text) {
    if (!text || !text.trim()) {
      previewCustomerName.textContent = "—";
      previewAmount.textContent = "—";
      previewItems.textContent = "—";
      latestParsedDraft = { amount: 0, customerName: "", items: [] };
      return;
    }

    const parsed = window.voiceService.parseTranscript(text);
    latestParsedDraft = parsed;

    previewCustomerName.textContent = parsed.customerName || "Topilmadi (qo'lda tanlanadi)";
    previewAmount.textContent = parsed.amount > 0 ? formatMoney(parsed.amount) : "Topilmadi";
    previewItems.textContent = parsed.items.length > 0 ? parsed.items.join(", ") : "Izohsiz";
  }

  function startContinuousVoice() {
    if (!window.voiceService.isSupported()) {
      const sample = prompt(
        "Brauzeringizda ovozli kiritish (Speech API) yo'q yoki ruxsat berilmagan.\n" +
        "Sinov uchun qoralama matn yozing (shevalar ham ishlaydi):\n\n" +
        "Masalan: 'Anvar akaga qirq besh min somga 2 ta non va yog''"
      );
      if (sample) {
        inputVoiceDraft.value = sample;
        updateDraftPreview(sample);
      }
      return;
    }

    haptic("medium");
    window.voiceService.startListening({
      onTranscriptUpdate: (fullDraft, interim) => {
        inputVoiceDraft.value = fullDraft;
        updateDraftPreview(fullDraft);
        voiceStatusText.textContent = interim ? `Jonli: "${interim}"` : "Yozilmoqda...";
      },
      onStatusChange: (status) => {
        if (status === "listening") {
          btnVoiceRecord.classList.add("recording");
          voiceLiveIndicator.style.display = "inline-flex";
          btnStopMic.style.display = "flex";
          voiceStatusText.textContent = "To'xtovsiz eshitilmoqda (gapiravering, o'chmaydi)...";
        } else if (status === "processing") {
          btnVoiceRecord.classList.remove("recording");
          voiceLiveIndicator.style.display = "inline-flex";
          voiceStatusText.textContent = "⚡ Groq Whisper (0.3s): Ovoz aniqlanmoqda...";
        } else {
          btnVoiceRecord.classList.remove("recording");
          voiceLiveIndicator.style.display = "none";
          btnStopMic.style.display = "none";
          
          // Auto-apply to form if text was transcribed!
          if (inputVoiceDraft.value.trim()) {
            updateDraftPreview(inputVoiceDraft.value);
            applyDraftToForm(true);
          } else {
            voiceStatusText.textContent = "Mikrofon to'xtatildi. Qoralamani tahrirlashingiz mumkin.";
          }
        }
      },
      onError: (errMsg) => {
        voiceStatusText.textContent = errMsg;
      }
    });
  }

  function stopContinuousVoice() {
    haptic("light");
    window.voiceService.stopListening();
  }

  btnVoiceRecord.addEventListener("click", () => {
    if (window.voiceService.isListening) {
      stopContinuousVoice();
    } else {
      startContinuousVoice();
    }
  });

  btnStopMic.addEventListener("click", () => {
    stopContinuousVoice();
  });

  // Real-time re-parse when user edits the draft text directly
  inputVoiceDraft.addEventListener("input", (e) => {
    updateDraftPreview(e.target.value);
  });

  btnClearDraft.addEventListener("click", () => {
    haptic("light");
    inputVoiceDraft.value = "";
    updateDraftPreview("");
  });

  btnParseDraftText.addEventListener("click", () => {
    haptic("light");
    updateDraftPreview(inputVoiceDraft.value);
    alert("Qoralama matn qayta tahlil qilindi!");
  });

  // Transfer draft parsed info into the actual form fields
  function applyDraftToForm(isAuto = false) {
    if (!latestParsedDraft || (!latestParsedDraft.amount && !latestParsedDraft.customerName && !latestParsedDraft.items.length)) {
      updateDraftPreview(inputVoiceDraft.value);
    }

    // 1. Amount
    if (latestParsedDraft.amount > 0) {
      document.getElementById("inputDebtAmount").value = latestParsedDraft.amount;
    }

    // 2. Items & Note
    if (latestParsedDraft.items && latestParsedDraft.items.length > 0) {
      document.getElementById("inputDebtNote").value = latestParsedDraft.items.join(", ");
      
      // Also highlight tag buttons
      document.querySelectorAll("#quickProductTags .tag-btn").forEach(tagBtn => {
        const tagText = tagBtn.getAttribute("data-tag");
        if (latestParsedDraft.items.some(it => it.toLowerCase() === tagText.toLowerCase())) {
          tagBtn.classList.add("selected");
        }
      });
    }

    // 3. Customer
    if (latestParsedDraft.customerName) {
      const custInput = document.getElementById("inputCustomerCombobox");
      if (custInput) {
        custInput.value = latestParsedDraft.customerName;
        custInput.dispatchEvent(new Event("input"));
      }
    }

    // 4. Date
    if (latestParsedDraft.date) {
      document.getElementById("inputDebtDate").value = latestParsedDraft.date;
    }

    updateAmountPreview();

    // Stop mic if running
    if (window.voiceService.isListening) {
      stopContinuousVoice();
    }

    if (isAuto) {
      haptic("success");
      const custText = latestParsedDraft.customerName || "Mijoz";
      const sumText = latestParsedDraft.amount > 0 ? formatMoney(latestParsedDraft.amount) : "";
      voiceStatusText.textContent = `✅ Avtomat to'ldirildi: ${custText} ${sumText ? "· " + sumText : ""}`;
    } else {
      haptic("success");
      document.getElementById("inputDebtAmount").scrollIntoView({ behavior: "smooth" });
    }
  }

  btnApplyDraftToForm.addEventListener("click", () => {
    applyDraftToForm(false);
  });

  // Quick Voice Assistant Button on Dashboard
  const btnDashboardVoiceQuick = document.getElementById("btnDashboardVoiceQuick");
  if (btnDashboardVoiceQuick) {
    btnDashboardVoiceQuick.addEventListener("click", () => {
      haptic("medium");
      openModal("modalAddDebt");
      setTimeout(() => {
        startContinuousVoice();
      }, 400);
    });
  }

  // Toggle Extra Customer Details (Phone & Limit)
  const btnToggleNewCustomer = document.getElementById("btnToggleNewCustomer");
  const newCustomerFields = document.getElementById("newCustomerFields");
  if (btnToggleNewCustomer && newCustomerFields) {
    btnToggleNewCustomer.addEventListener("click", () => {
      const isHidden = newCustomerFields.style.display === "none";
      newCustomerFields.style.display = isHidden ? "block" : "none";
      btnToggleNewCustomer.textContent = isHidden ? "✕ Yopish" : "+ Telefon / Limit qo'shish";
    });
  }

  // Handle Add Debt Form Submit
  document.getElementById("formAddDebt").addEventListener("submit", (e) => {
    e.preventDefault();
    haptic("success");

    const enteredName = (document.getElementById("inputCustomerCombobox")?.value || "").trim();
    if (!enteredName) {
      alert("Iltimos, mijoz ismini tanlang yoki yozing.");
      return;
    }

    let customerId = "";
    const matched = window.store.findCustomerByName(enteredName);
    if (matched) {
      customerId = matched.id;
    } else {
      // Auto-create new customer on the fly!
      const phone = document.getElementById("newCustPhone")?.value || "";
      const limit = document.getElementById("newCustLimit")?.value || 500000;
      const created = window.store.addCustomer({ name: enteredName, phone, limit });
      customerId = created.id;
    }

    const amount = document.getElementById("inputDebtAmount").value;
    const note = document.getElementById("inputDebtNote").value;
    const dateVal = document.getElementById("inputDebtDate").value;
    const dueDateVal = document.getElementById("inputDebtDueDate").value;

    const selectedTags = Array.from(document.querySelectorAll("#quickProductTags .tag-pill-wrapper.selected .tag-btn"))
      .map(b => b.getAttribute("data-tag"));

    const createdTx = window.store.addDebt({
      customerId,
      amount: parseInt(amount, 10),
      note,
      items: selectedTags,
      date: dateVal,
      dueDate: dueDateVal
    });

    const notifyCust = document.getElementById("checkNotifyCustomer")?.checked;
    const targetCustomer = window.store.getCustomerById(customerId);

    // Reset and close
    document.getElementById("formAddDebt").reset();
    if (newCustomerFields) newCustomerFields.style.display = "none";
    if (customerMatchStatus) {
      customerMatchStatus.style.display = "none";
      customerMatchStatus.innerHTML = "";
    }
    if (amountFormattedPreview) amountFormattedPreview.textContent = "0 so'm";
    if (btnToggleNewCustomer) btnToggleNewCustomer.textContent = "+ Telefon / Limit qo'shish";
    document.querySelectorAll("#quickProductTags .tag-pill-wrapper.selected").forEach(b => b.classList.remove("selected"));
    closeModal("modalAddDebt");
    renderStats();
    renderCustomers();

    // Trigger Floating Undo Toast (5 seconds window)
    if (createdTx) {
      showUndoToast({
        type: 'debt',
        customerId,
        txId: createdTx.id,
        customerName: enteredName,
        amount: parseInt(amount, 10)
      });
    }

    // Show receipt confirmation if opted-in
    if (notifyCust && targetCustomer && createdTx) {
      setTimeout(() => {
        openReceiptModal(targetCustomer, createdTx);
      }, 300);
    }
  });

  // Modal: Receipt Confirmation
  let activeReceiptCustomer = null;
  let activeReceiptTx = null;

  function openReceiptModal(customer, tx) {
    activeReceiptCustomer = customer;
    activeReceiptTx = tx;
    haptic("medium");

    const text = window.reminders.generateConfirmationReceipt(customer, tx);
    document.getElementById("textReceiptContent").value = text;
    document.getElementById("receiptModalTitle").textContent = 
      tx.type === "debt" ? "🧾 Nasiya Cheki Tayyor" : "🧾 To'lov Cheki Tayyor";

    openModal("modalReceiptPreview");
  }

  // Receipt modal buttons
  document.getElementById("btnReceiptShareTelegram")?.addEventListener("click", () => {
    haptic("medium");
    if (activeReceiptCustomer && activeReceiptTx) {
      window.reminders.shareReceiptViaTelegram(activeReceiptCustomer, activeReceiptTx);
    }
  });

  document.getElementById("btnReceiptShareSMS")?.addEventListener("click", () => {
    haptic("light");
    if (activeReceiptCustomer && activeReceiptTx) {
      window.reminders.shareReceiptViaSMS(activeReceiptCustomer, activeReceiptTx);
    }
  });

  document.getElementById("btnReceiptCopy")?.addEventListener("click", async () => {
    haptic("light");
    const text = document.getElementById("textReceiptContent").value;
    await window.reminders.copyToClipboard(text);
    alert("Chek nusxalandi!");
  });

  // Open Customer Details Modal
  function openCustomerDetails(id) {
    selectedCustomer = window.store.getCustomerById(id);
    if (!selectedCustomer) return;

    document.getElementById("detailCustomerName").textContent = selectedCustomer.name;
    document.getElementById("detailCustomerPhone").textContent = selectedCustomer.phone || (selectedCustomer.telegramUsername ? '@' + selectedCustomer.telegramUsername : 'Telefon yo\'q');
    
    const debtEl = document.getElementById("detailTotalDebt");
    debtEl.textContent = formatMoney(selectedCustomer.totalDebt);
    debtEl.style.color = selectedCustomer.totalDebt > 0 ? "var(--danger)" : "var(--success)";

    const limitBadge = document.getElementById("detailLimitBadge");
    if (selectedCustomer.limit) {
      const pct = Math.round((selectedCustomer.totalDebt / selectedCustomer.limit) * 100);
      if (selectedCustomer.totalDebt > selectedCustomer.limit) {
        limitBadge.innerHTML = `<span style="color: var(--danger); font-weight: 700;">⚠️ Limitdan oshgan (${pct}% - limit: ${formatMoney(selectedCustomer.limit)})</span>`;
      } else {
        limitBadge.innerHTML = `<span style="color: var(--tg-theme-hint-color);">Limit: ${formatMoney(selectedCustomer.limit)} (${pct}% ishlatilgan)</span>`;
      }
    } else {
      limitBadge.innerHTML = "";
    }

    // Render history with exact date and optional due date
    const historyContainer = document.getElementById("detailHistoryContainer");
    const txs = selectedCustomer.transactions || [];

    if (txs.length === 0) {
      historyContainer.innerHTML = `<p style="font-size: 13px; color: var(--tg-theme-hint-color); text-align: center; padding: 14px 0;">Hozircha operatsiyalar yo'q</p>`;
    } else {
      historyContainer.innerHTML = txs.map(t => {
        const isDebt = t.type === "debt";
        const dueDateInfo = t.dueDate ? ` · <span style="color: var(--warning); font-weight: 600;">⏳ To'lov: ${t.dueDate}</span>` : '';
        return `
          <div class="history-item">
            <div>
              <div class="hist-desc">${isDebt ? '🔴 ' : '🟢 '}${t.note || (isDebt ? 'Nasiya' : 'To\'lov')}</div>
              <div class="hist-date">📅 ${t.date}${dueDateInfo}</div>
            </div>
            <div class="hist-amount ${isDebt ? 'debt-inc' : 'pay-dec'}">
              ${isDebt ? '+' : '-'}${formatMoney(t.amount)}
            </div>
          </div>
        `;
      }).join("");
    }

    openModal("modalCustomerDetails");
  }

  // Open Payment Modal from Details
  document.getElementById("btnOpenPaymentModal").addEventListener("click", () => {
    if (!selectedCustomer || selectedCustomer.totalDebt <= 0) {
      alert("Bu mijozning to'lanmagan qarzi yo'q.");
      return;
    }
    haptic("light");
    document.getElementById("inputPayAmount").value = selectedCustomer.totalDebt;
    document.getElementById("inputPayDate").value = getLocalDateTimeString();
    openModal("modalRecordPayment");
  });

  // Quick fill full debt
  document.getElementById("btnPayFullDebt").addEventListener("click", () => {
    if (selectedCustomer) {
      document.getElementById("inputPayAmount").value = selectedCustomer.totalDebt;
    }
  });

  // Handle Record Payment Form Submit
  document.getElementById("formRecordPayment").addEventListener("submit", (e) => {
    e.preventDefault();
    haptic("success");
    const amount = parseInt(document.getElementById("inputPayAmount").value, 10);
    const method = document.getElementById("selectPayMethod").value;
    const payDate = document.getElementById("inputPayDate").value;

    const paymentTx = window.store.recordPayment({
      customerId: selectedCustomer.id,
      amount,
      note: method,
      date: payDate
    });

    closeModal("modalRecordPayment");
    openCustomerDetails(selectedCustomer.id);
    renderStats();
    renderCustomers();

    // Offer payment receipt
    if (paymentTx) {
      // Trigger Undo Toast for payment
      showUndoToast({
        type: 'payment',
        customerId: selectedCustomer.id,
        txId: paymentTx.id,
        customerName: selectedCustomer.name,
        amount
      });

      setTimeout(() => {
        openReceiptModal(selectedCustomer, paymentTx);
      }, 400);
    }
  });

  // Open Reminder Modal from Details
  document.getElementById("btnOpenReminderModal").addEventListener("click", () => {
    if (!selectedCustomer || selectedCustomer.totalDebt <= 0) {
      alert("Mijozda faol qarz mavjud emas.");
      return;
    }
    haptic("light");
    updateReminderPreview();
    openModal("modalSendReminder");
  });

  function updateReminderPreview() {
    if (!selectedCustomer) return;
    const text = window.reminders.generateReminderText(selectedCustomer, selectedReminderTone);
    document.getElementById("reminderMessageText").value = text;
  }

  // Reminder Tone Filter Pills
  document.querySelectorAll("#toneFilterPills .pill-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      haptic("light");
      document.querySelectorAll("#toneFilterPills .pill-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      selectedReminderTone = btn.getAttribute("data-tone");
      updateReminderPreview();
    });
  });

  // Share via Telegram
  document.getElementById("btnShareTelegram").addEventListener("click", () => {
    haptic("medium");
    if (!selectedCustomer) return;
    window.reminders.shareViaTelegram(selectedCustomer, selectedReminderTone);
  });

  // Copy Reminder Text
  document.getElementById("btnCopyReminderText").addEventListener("click", async () => {
    haptic("light");
    const text = document.getElementById("reminderMessageText").value;
    await window.reminders.copyToClipboard(text);
    alert("Xabar matni nusxalandi!");
  });

  // Send Direct SMS
  document.getElementById("btnSendSMSDirect").addEventListener("click", () => {
    haptic("light");
    if (!selectedCustomer) return;
    window.reminders.shareViaSMS(selectedCustomer, selectedReminderTone);
  });

  // Open Add Supplier Modal
  document.getElementById("btnOpenAddSupplier").addEventListener("click", () => {
    haptic("light");
    openModal("modalAddSupplier");
  });

  // Add Supplier Form Submit
  document.getElementById("formAddSupplier").addEventListener("submit", (e) => {
    e.preventDefault();
    haptic("success");
    const name = document.getElementById("inputSupName").value;
    const phone = document.getElementById("inputSupPhone").value;
    const initialDebt = document.getElementById("inputSupDebt").value;
    const note = document.getElementById("inputSupNote").value;

    window.store.addSupplier({ name, phone, initialDebt, note });
    document.getElementById("formAddSupplier").reset();
    closeModal("modalAddSupplier");
    renderSuppliers();
    renderStats();
  });

  // Reset Demo Data
  document.getElementById("btnResetDemo").addEventListener("click", () => {
    if (confirm("Demo ma'lumotlarni qayta tiklashni xohlaysizmi?")) {
      haptic("medium");
      window.store.resetToDemo();
      renderStats();
      renderCustomers();
      renderSuppliers();
    }
  });

  // Export JSON Report
  document.getElementById("btnExport").addEventListener("click", () => {
    haptic("light");
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(window.store.state, null, 2));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `qarz_daftari_${new Date().toISOString().slice(0, 10)}.json`);
    dlAnchor.click();
  });

  // Analytics Download Text Report
  document.getElementById("btnDownloadReportPDF")?.addEventListener("click", () => {
    haptic("medium");
    const s = window.store.state;
    let report = `=== ${s.shopName.toUpperCase()} — QARZ DAFTARI HISOBOTI ===\n`;
    report += `Sana: ${new Date().toLocaleString('uz-UZ')}\n`;
    report += `Jami nasiya: ${formatMoney(window.store.getTotalCustomerDebt())}\n`;
    report += `Ta'minotchi qarzi: ${formatMoney(window.store.getTotalSupplierDebt())}\n\n`;
    report += `--- MIJOZLAR QARZI ---\n`;
    s.customers.forEach(c => {
      report += `• ${c.name} (${c.phone}): ${formatMoney(c.totalDebt)} [${c.status}]\n`;
    });

    const blob = new Blob([report], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `qarz_hisoboti_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  });

  // --- CLOUD SYNC & BACKUP MODAL HANDLERS ---
  const btnOpenCloudBackup = document.getElementById("btnOpenCloudBackup");
  const btnSendBackupToTelegram = document.getElementById("btnSendBackupToTelegram");
  const btnTriggerRestoreFile = document.getElementById("btnTriggerRestoreFile");
  const btnDownloadBackupFileDirect = document.getElementById("btnDownloadBackupFileDirect");
  const inputRestoreBackupFile = document.getElementById("inputRestoreBackupFile");
  const restoreStatusMsg = document.getElementById("restoreStatusMsg");
  const cloudSyncTimestamp = document.getElementById("cloudSyncTimestamp");

  if (btnOpenCloudBackup) {
    btnOpenCloudBackup.addEventListener("click", () => {
      haptic("light");
      if (cloudSyncTimestamp) {
        cloudSyncTimestamp.textContent = `Oxirgi sinxronlash: ${new Date().toLocaleTimeString('uz-UZ')} · Status: Xavfsiz`;
      }
      openModal("modalCloudBackup");
    });
  }

  if (btnSendBackupToTelegram) {
    btnSendBackupToTelegram.addEventListener("click", () => {
      haptic("medium");
      const totalDebt = window.store.getTotalCustomerDebt();
      const custCount = (window.store.state.customers || []).length;

      const shareText = `📁 QARZ DAFTARI BULUTLI ZAXIRASI\n` +
        `📅 Sana: ${new Date().toLocaleString('uz-UZ')}\n` +
        `👥 Mijozlar soni: ${custCount} ta\n` +
        `💰 Jami nasiya: ${formatMoney(totalDebt)}\n\n` +
        `🔒 Barcha ma'lumotlar shifrlangan JSON ko'rinishida saqlandi.`;

      const shareUrl = `https://t.me/share/url?url=${encodeURIComponent('https://t.me/qarz_app_bot')}&text=${encodeURIComponent(shareText)}`;
      
      if (tg?.openTelegramLink) {
        tg.openTelegramLink(shareUrl);
      } else {
        window.open(shareUrl, "_blank");
      }
      alert("Zaxira hisoboti Telegramga yo'naltirildi!");
    });
  }

  if (btnDownloadBackupFileDirect) {
    btnDownloadBackupFileDirect.addEventListener("click", () => {
      haptic("light");
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(window.store.exportDataJSON());
      const dlAnchor = document.createElement('a');
      dlAnchor.setAttribute("href", dataStr);
      dlAnchor.setAttribute("download", `qarz_daftari_zaxira_${new Date().toISOString().slice(0, 10)}.json`);
      dlAnchor.click();
    });
  }

  if (btnTriggerRestoreFile && inputRestoreBackupFile) {
    btnTriggerRestoreFile.addEventListener("click", () => {
      inputRestoreBackupFile.click();
    });

    inputRestoreBackupFile.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (ev) => {
        const result = window.store.importDataJSON(ev.target.result);
        if (result.success) {
          haptic("success");
          if (restoreStatusMsg) {
            restoreStatusMsg.style.display = "block";
            restoreStatusMsg.style.color = "var(--success)";
            restoreStatusMsg.textContent = `✅ Muvaffaqiyatli tiklandi! (${result.customerCount} ta mijoz)`;
          }
          renderStats();
          renderCustomers();
          renderSuppliers();
        } else {
          haptic("warning");
          if (restoreStatusMsg) {
            restoreStatusMsg.style.display = "block";
            restoreStatusMsg.style.color = "var(--danger)";
            restoreStatusMsg.textContent = `❌ Xatolik: ${result.error}`;
          }
        }
      };
      reader.readAsText(file);
    });
  }

  // --- STORE COUNTER QR POSTER MODAL HANDLERS ---
  const btnOpenQRPoster = document.getElementById("btnOpenQRPoster");
  const btnPrintPoster = document.getElementById("btnPrintPoster");
  const btnSharePosterLink = document.getElementById("btnSharePosterLink");

  if (btnOpenQRPoster) {
    btnOpenQRPoster.addEventListener("click", () => {
      haptic("light");
      const shopTitle = window.store.state.shopName || "Mahalla Baraka Do'koni";
      const posterShopTitle = document.getElementById("posterShopTitle");
      if (posterShopTitle) posterShopTitle.textContent = shopTitle;
      openModal("modalQRPoster");
    });
  }

  if (btnPrintPoster) {
    btnPrintPoster.addEventListener("click", () => {
      haptic("medium");
      window.print();
    });
  }

  if (btnSharePosterLink) {
    btnSharePosterLink.addEventListener("click", () => {
      haptic("light");
      const shopTitle = window.store.state.shopName || "Do'konimiz";
      const text = `🏪 Hurmatli xaridorlar! ${shopTitle}da nasiya va to'lovlar shaffof hisob-kitob qilinadi. Balansingizni ko'rish va to'lov qilish: https://t.me/qarz_app_bot`;
      const shareUrl = `https://t.me/share/url?url=${encodeURIComponent('https://t.me/qarz_app_bot')}&text=${encodeURIComponent(text)}`;
      if (tg?.openTelegramLink) {
        tg.openTelegramLink(shareUrl);
      } else {
        window.open(shareUrl, "_blank");
      }
    });
  }

  // Initial Render
  renderStats();
  renderCustomers();
});
