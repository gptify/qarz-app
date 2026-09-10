import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def run_receipt_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        await page.goto("http://localhost:8085/index.html")

        # 1. Open Add Debt modal
        await page.click("#btnNavAddDebt")
        await page.wait_for_timeout(400)

        # Fill 85,000 UZS and select product tag
        await page.click('button[data-add="50000"]')
        await page.click('button[data-add="20000"]')
        await page.click('button[data-tag="Go\'sht"]')

        # Verify notify checkbox is checked
        is_checked = await page.is_checked("#checkNotifyCustomer")
        print("Notify customer checkbox checked:", is_checked)
        assert is_checked

        # 2. Submit debt form
        await page.click('#formAddDebt button[type="submit"]')
        await page.wait_for_timeout(600)

        # 3. Verify receipt modal automatically appeared
        receipt_modal = await page.query_selector("#modalReceiptPreview.open")
        assert receipt_modal is not None
        print("Receipt modal automatically opened upon saving!")

        receipt_text = await page.input_value("#textReceiptContent")
        print("Receipt content length:", len(receipt_text))
        assert "YANGI NASIYA XARIDI CHEKI" in receipt_text
        assert "Go'sht" in receipt_text or "70,000" in receipt_text

        # 4. Take screenshot
        shot_path = Path(__file__).resolve().parent / "qarz_receipt_confirmation.png"
        await page.screenshot(path=str(shot_path))
        print(f"Saved receipt screenshot to {shot_path}")

        await browser.close()
        print("Receipt confirmation test passed 100% successfully!")

if __name__ == "__main__":
    asyncio.run(run_receipt_test())
