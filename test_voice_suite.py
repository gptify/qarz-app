import asyncio
from playwright.async_api import async_playwright

async def run_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 390, "height": 844})
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print("[*] Navigating to http://localhost:8085 ...")
        await page.goto("http://localhost:8085", wait_until="networkidle")

        # Check title
        title = await page.title()
        print(f"[+] Page title: {title}")
        assert "Qarz Daftari" in title

        # Check Quick Voice button on Dashboard
        quick_voice = await page.query_selector("#btnDashboardVoiceQuick")
        assert quick_voice is not None, "Quick voice button missing"
        print("[+] #btnDashboardVoiceQuick exists")

        # Open modalAddDebt
        await page.click("#btnNavAddDebt")
        await page.wait_for_selector("#modalAddDebt.open", timeout=3000)
        print("[+] #modalAddDebt opened successfully")

        # Check elements inside voice-draft-section
        voice_rec = await page.query_selector("#btnVoiceRecord")
        audio_preview = await page.query_selector("#audioPreviewBox")
        mic_help = await page.query_selector("#micHelpBanner")
        draft_box = await page.query_selector("#inputVoiceDraft")
        assert voice_rec is not None
        assert audio_preview is not None
        assert mic_help is not None
        assert draft_box is not None
        print("[+] All voice UI elements (audioPreviewBox, micHelpBanner, inputVoiceDraft) verified!")

        # Test VoiceInputService parsing in browser context
        parse_test = await page.evaluate("""() => {
            const service = window.voiceService;
            const parsed = service.parseTranscript("Akmal akaga ellik ming so'm 2 ta non bilan yog'");
            return {
                hasService: !!service,
                hasGeminiKey: !!service.geminiApiKey,
                parsedAmount: parsed.amount,
                parsedCustomer: parsed.customerName,
                parsedItems: parsed.items
            };
        }""")
        print("[+] VoiceInputService in-browser test:", parse_test)
        assert parse_test["hasService"] is True
        assert parse_test["hasGeminiKey"] is True
        assert parse_test["parsedAmount"] == 50000
        assert len(parse_test["parsedCustomer"]) > 0

        # Test URL Autofill
        print("[*] Testing URL Autofill params: ?autofill=true&customer=Rustam+aka&amount=75000&items=go%27sht")
        await page.goto("http://localhost:8085?autofill=true&customer=Rustam+aka&amount=75000&items=go%27sht", wait_until="networkidle")
        await page.wait_for_selector("#modalAddDebt.open", timeout=3000)

        cust_val = await page.input_value("#inputCustomerCombobox")
        amount_val = await page.input_value("#inputDebtAmount")
        note_val = await page.input_value("#inputDebtNote")
        print(f"[+] Autofill result -> Customer: '{cust_val}', Amount: '{amount_val}', Note: '{note_val}'")
        assert "Rustam" in cust_val
        assert amount_val == "75000"

        # Check console errors
        print(f"[*] Console errors count: {len(console_errors)}")
        if console_errors:
            print("Errors:", console_errors)
        assert len(console_errors) == 0, f"Found console errors: {console_errors}"

        print("\n[SUCCESS] ALL VOICE SUITE TESTS PASSED 100%!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_test())
