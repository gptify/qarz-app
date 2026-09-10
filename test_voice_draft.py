import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def run_voice_draft_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        await page.goto("http://localhost:8085/index.html")

        # 1. Verify Quick Voice Bar on Dashboard
        quick_voice = await page.query_selector("#btnDashboardVoiceQuick")
        assert quick_voice is not None
        print("Quick Voice bar verified on dashboard.")

        # 2. Click Quick Voice bar -> opens modal
        await quick_voice.click()
        await page.wait_for_timeout(500)

        # Verify draft studio elements
        draft_box = await page.query_selector("#inputVoiceDraft")
        assert draft_box is not None

        # 3. Simulate dialect speech typing
        dialect_speech = "Anvar akaga qirq besh min somga 2 ta non va yog'"
        await page.fill("#inputVoiceDraft", dialect_speech)
        await page.dispatch_event("#inputVoiceDraft", "input")
        await page.wait_for_timeout(400)

        # 4. Check real-time parsed preview card
        preview_cust = await page.inner_text("#previewCustomerName")
        preview_amount = await page.inner_text("#previewAmount")
        preview_items = await page.inner_text("#previewItems")

        print(f"Parsed Preview -> Customer: {preview_cust}, Amount: {preview_amount}, Items: {preview_items}")
        assert "Anvar" in preview_cust
        assert "45 000" in preview_amount or "45,000" in preview_amount or "45000" in preview_amount
        assert "Non" in preview_items and "Yog'" in preview_items

        # Screenshot of the Draft Voice Studio
        screenshot_path = Path(__file__).resolve().parent / "qarz_voice_draft_studio.png"
        await page.screenshot(path=str(screenshot_path))
        print(f"Draft studio screenshot saved to {screenshot_path}")

        # 5. Click 'Apply Draft to Form'
        await page.click("#btnApplyDraftToForm")
        await page.wait_for_timeout(400)

        form_amount = await page.input_value("#inputDebtAmount")
        form_note = await page.input_value("#inputDebtNote")
        print(f"Form Fields -> Amount: {form_amount}, Note: {form_note}")
        assert form_amount == "45000"
        assert "Non" in form_note and "Yog'" in form_note

        await browser.close()
        print("Voice draft & dialect parser test passed 100% successfully!")

if __name__ == "__main__":
    asyncio.run(run_voice_draft_test())
