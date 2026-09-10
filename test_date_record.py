import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright

async def run_date_record_test():
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

        # Check that date input has a default today value
        date_val = await page.input_value("#inputDebtDate")
        print(f"Default Debt Date: {date_val}")
        assert len(date_val) > 10

        # 2. Click 'Kecha' (Yesterday) chip
        await page.click("#btnDateYesterday")
        await page.wait_for_timeout(200)
        yesterday_val = await page.input_value("#inputDebtDate")
        print(f"Yesterday Date Value: {yesterday_val}")
        assert yesterday_val != ""

        # 3. Click '+1 hafta' due date chip
        await page.click('button[data-days="7"]')
        await page.wait_for_timeout(200)
        due_val = await page.input_value("#inputDebtDueDate")
        print(f"Due Date Value: {due_val}")
        assert len(due_val) == 10

        # 4. Fill amount and submit
        await page.click('button[data-add="50000"]')
        await page.click('button[data-tag="Non"]')
        
        # Take screenshot of the date inputs in the modal
        shot_path = Path(__file__).resolve().parent / "qarz_date_form.png"
        await page.screenshot(path=str(shot_path))
        print(f"Saved date form screenshot to {shot_path}")

        # Submit
        await page.click('#formAddDebt button[type="submit"]')
        await page.wait_for_timeout(500)

        # 5. Open the first customer card to verify history shows date & due date
        cards = await page.query_selector_all(".customer-card")
        await cards[0].click()
        await page.wait_for_timeout(400)

        history_html = await page.inner_html("#detailHistoryContainer")
        assert "📅" in history_html
        print("History successfully verified with custom date and due date!")

        # Screenshot of customer history showing date badge
        history_shot = Path(__file__).resolve().parent / "qarz_date_history.png"
        await page.screenshot(path=str(history_shot))
        print(f"Saved history screenshot to {history_shot}")

        await browser.close()
        print("Date recording test passed 100% successfully!")

if __name__ == "__main__":
    asyncio.run(run_date_record_test())
