import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

async def run_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()

        # Load file directly
        file_path = Path(__file__).resolve().parent / "index.html"
        url = file_path.as_uri()
        print(f"Loading {url}...")
        await page.goto(url)

        # 1. Check title & stats
        title = await page.inner_text("#headerShopTitle")
        print(f"Shop Title: {title}")
        total_debt = await page.inner_text("#totalDebtDisplay")
        print(f"Total Debt: {total_debt}")
        assert "so'm" in total_debt

        # 2. Check customer cards
        cards = await page.query_selector_all(".customer-card")
        print(f"Rendered {len(cards)} customer cards.")
        assert len(cards) >= 4

        # Take main view screenshot
        screenshot_path = Path(__file__).resolve().parent / "qarz_tma_preview.png"
        await page.screenshot(path=str(screenshot_path))
        print(f"Screenshot saved to {screenshot_path}")

        # 3. Click first customer card
        await cards[0].click()
        await page.wait_for_timeout(500)
        modal_name = await page.inner_text("#detailCustomerName")
        print(f"Opened details modal for: {modal_name}")
        assert len(modal_name) > 0

        # Take detail modal screenshot
        detail_screenshot = Path(__file__).resolve().parent / "qarz_tma_modal.png"
        await page.screenshot(path=str(detail_screenshot))

        # Close modal
        await page.click('[data-close="modalCustomerDetails"]')
        await page.wait_for_timeout(300)

        # 4. Open Add Debt modal
        await page.click("#btnNavAddDebt")
        await page.wait_for_timeout(500)
        # Select product tag 'Non'
        await page.click('button[data-tag="Non"]')
        # Enter amount +50 ming
        await page.click('button[data-add="50000"]')
        
        add_screenshot = Path(__file__).resolve().parent / "qarz_tma_add_debt.png"
        await page.screenshot(path=str(add_screenshot))

        # Submit form
        await page.click('#formAddDebt button[type="submit"]')
        await page.wait_for_timeout(500)

        new_total_debt = await page.inner_text("#totalDebtDisplay")
        print(f"Updated Total Debt after adding 50,000: {new_total_debt}")

        await browser.close()
        print("All automated UI tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_test())
