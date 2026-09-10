import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def run_additional_tests():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        file_path = Path(__file__).resolve().parent / "index.html"
        await page.goto(file_path.as_uri())

        # Click first card
        cards = await page.query_selector_all(".customer-card")
        await cards[0].click()
        await page.wait_for_timeout(400)

        # Open reminder modal
        await page.click("#btnOpenReminderModal")
        await page.wait_for_timeout(400)
        rem_screenshot = Path(__file__).resolve().parent / "qarz_tma_reminder.png"
        await page.screenshot(path=str(rem_screenshot))
        print("Reminder modal screenshot saved.")

        # Test clicking tone "Juma"
        await page.click('button[data-tone="juma"]')
        await page.wait_for_timeout(300)
        juma_text = await page.input_value("#reminderMessageText")
        print("Juma tone text generated successfully:", "Juma" in juma_text)
        assert "Juma" in juma_text

        # Close reminder modal and open payment modal
        await page.click('[data-close="modalSendReminder"]')
        await page.wait_for_timeout(300)
        await page.click("#btnOpenPaymentModal")
        await page.wait_for_timeout(400)
        pay_screenshot = Path(__file__).resolve().parent / "qarz_tma_payment.png"
        await page.screenshot(path=str(pay_screenshot))
        print("Payment modal screenshot saved.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_additional_tests())
