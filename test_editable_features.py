import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def run_editable_test():
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

        # 2. Test Editable Customer Combobox with a brand new name
        new_customer_name = "Sherzod aka (Usta)"
        await page.fill("#inputCustomerCombobox", new_customer_name)
        await page.dispatch_event("#inputCustomerCombobox", "input")
        await page.wait_for_timeout(300)

        status_html = await page.inner_html("#customerMatchStatus")
        assert "Yangi mijoz" in status_html
        print("Customer match status verified.")

        # 3. Test adding a new custom product tag
        await page.click("#btnOpenAddTag")
        await page.wait_for_timeout(200)
        await page.fill("#inputNewTagName", "Kola 1.5L")
        await page.click("#btnConfirmAddTag")
        await page.wait_for_timeout(300)

        # Verify new tag is rendered and select it
        new_tag = await page.query_selector('button[data-tag="Kola 1.5L"]')
        assert new_tag is not None
        await new_tag.click()
        print("Successfully added and selected custom tag 'Kola 1.5L'")

        # 4. Test Editable Summa Section & Quick Chips & Clear
        await page.click('button[data-add="100000"]')
        await page.click('button[data-add="50000"]')
        await page.wait_for_timeout(200)
        amt_val = await page.input_value("#inputDebtAmount")
        assert amt_val == "150000"

        # Test Clear Button 'C'
        await page.click("#btnClearAmount")
        await page.wait_for_timeout(200)
        cleared_val = await page.input_value("#inputDebtAmount")
        assert cleared_val == ""

        # Enter final amount
        await page.fill("#inputDebtAmount", "85000")
        await page.dispatch_event("#inputDebtAmount", "input")
        preview_text = await page.inner_text("#amountFormattedPreview")
        print(f"Live Amount Preview: {preview_text}")
        assert "85,000" in preview_text

        # Uncheck notify customer so it closes directly without receipt modal
        await page.uncheck("#checkNotifyCustomer")

        # Take screenshot of the editable form state
        shot_path = Path(__file__).resolve().parent / "qarz_editable_features.png"
        await page.screenshot(path=str(shot_path))
        print(f"Saved editable features screenshot to {shot_path}")

        # 5. Submit form
        await page.click('#formAddDebt button[type="submit"]')
        await page.wait_for_timeout(500)

        # 6. Verify newly created customer appears in customer list
        cards_text = await page.inner_text("#customerListContainer")
        assert "Sherzod aka" in cards_text
        print("New customer 'Sherzod aka (Usta)' successfully added and displayed with debt!")

        await browser.close()
        print("All editable feature tests passed 100% successfully!")

if __name__ == "__main__":
    asyncio.run(run_editable_test())
