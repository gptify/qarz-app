// Mock data for Qarz App TMA (Uzbekistan small retail shops)
window.INITIAL_DATA = {
  shopName: "Mahalla Baraka Do'koni",
  ownerPhone: "+998 90 123 45 67",
  currency: "so'm",
  customers: [
    {
      id: "c_1",
      name: "Anvar aka (12-uy)",
      phone: "+998 90 987 65 43",
      telegramUsername: "anvar_aka",
      limit: 1000000,
      totalDebt: 345000,
      lastTransactionDate: "2026-09-06",
      status: "active", // active, overdue, settled
      transactions: [
        {
          id: "t_101",
          type: "debt", // debt or payment
          amount: 185000,
          date: "2026-09-02 18:24",
          note: "Yog' 5L, shakar 2kg, un 1-nav",
          items: ["Yog' 5L", "Shakar 2kg", "Un"]
        },
        {
          id: "t_102",
          type: "debt",
          amount: 160000,
          date: "2026-09-06 20:10",
          note: "Go'sht 1.5kg, non 4ta",
          items: ["Go'sht 1.5kg", "Non 4ta"]
        }
      ]
    },
    {
      id: "c_2",
      name: "Dilshod sartarosh",
      phone: "+998 93 555 12 34",
      telegramUsername: "dilshod_barber",
      limit: 400000,
      totalDebt: 480000, // Exceeded limit!
      lastTransactionDate: "2026-08-18",
      status: "overdue",
      transactions: [
        {
          id: "t_103",
          type: "debt",
          amount: 480000,
          date: "2026-08-18 11:30",
          note: "Choy, kofe, pechene blok, energetik",
          items: ["Kofe", "Choy", "Pechene", "Energetik"]
        }
      ]
    },
    {
      id: "c_3",
      name: "Lola opa (O'qituvchi)",
      phone: "+998 97 111 22 33",
      telegramUsername: "lola_muallim",
      limit: 600000,
      totalDebt: 125000,
      lastTransactionDate: "2026-09-05",
      status: "active",
      transactions: [
        {
          id: "t_104",
          type: "debt",
          amount: 225000,
          date: "2026-09-01 19:00",
          note: "Sut, qatiq, sariyog', pishloq",
          items: ["Sut", "Qatiq", "Sariyog'"]
        },
        {
          id: "t_105",
          type: "payment",
          amount: 100000,
          date: "2026-09-05 14:15",
          note: "Click orqali to'lov",
          items: []
        }
      ]
    },
    {
      id: "c_4",
      name: "Nodir aka (Taksist)",
      phone: "+998 99 333 44 55",
      telegramUsername: "nodir_taxi",
      limit: 300000,
      totalDebt: 75000,
      lastTransactionDate: "2026-09-07",
      status: "active",
      transactions: [
        {
          id: "t_106",
          type: "debt",
          amount: 75000,
          date: "2026-09-07 08:40",
          note: "Non 3ta, mineral suv, Winston",
          items: ["Non", "Mineral suv", "Sigaret"]
        }
      ]
    },
    {
      id: "c_5",
      name: "Sanjar (Quruvchi)",
      phone: "+998 91 777 88 99",
      telegramUsername: "",
      limit: 500000,
      totalDebt: 0,
      lastTransactionDate: "2026-09-04",
      status: "settled",
      transactions: [
        {
          id: "t_107",
          type: "debt",
          amount: 320000,
          date: "2026-08-25 17:00",
          note: "Ichimliklar, chips, shirinliklar",
          items: []
        },
        {
          id: "t_108",
          type: "payment",
          amount: 320000,
          date: "2026-09-04 12:00",
          note: "Naqd pul bilan to'liq yopildi",
          items: []
        }
      ]
    }
  ],
  suppliers: [
    {
      id: "s_1",
      name: "Coca-Cola Distribyutor (Bobur)",
      phone: "+998 90 321 00 11",
      totalDebt: 1250000,
      lastDate: "2026-09-03",
      note: "5 blok 1.5L Fanta, 10 blok 0.5L Cola"
    },
    {
      id: "s_2",
      name: "Samarqand Nonvoyxonasi (Usta Rahmon)",
      phone: "+998 93 456 78 90",
      totalDebt: 380000,
      lastDate: "2026-09-07",
      note: "Ertalabki 120 ta patir va obi non"
    },
    {
      id: "s_3",
      name: "Muzqaymoq & Shirinliklar (Iroda)",
      phone: "+998 94 999 00 88",
      totalDebt: 620000,
      lastDate: "2026-08-30",
      note: "Plombir va tortlar partiyasi"
    }
  ],
  quickProducts: [
    "Non", "Yog'", "Go'sht", "Shakar", "Sut/Qatiq", "Tuxum", "Choy", "Un", "Meva/Sabzavot", "Sigaret", "Ichimlik"
  ]
};
