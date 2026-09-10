import os
import sys
import io
import re

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

def clean_num(s):
    return re.sub(r'[^\d]', '', s)

def test_all_improvements():
    artifact_dir = r"C:\Users\Shuxrat\.gemini\antigravity\brain\b9e389f5-9ae5-40ac-9593-b47094f2caba"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 412, "height": 915})
        page = context.new_page()

        print("\n--- 1. Navigating to Qarz TMA ---")
        page.goto("http://localhost:8085/index.html")
        page.wait_for_selector("#totalDebtDisplay")
        initial_debt_text = page.locator("#totalDebtDisplay").inner_text()
        initial_debt_num = clean_num(initial_debt_text)
        print(f"Initial Total Debt: {initial_debt_text} (Numeric: {initial_debt_num})")

        # --- 2. Test In-App POS Numpad ---
        print("\n--- 2. Testing In-App POS Numpad ---")
        page.click("#btnNavAddDebt")
        page.wait_for_selector("#modalAddDebt.open")

        # Verify POS Numpad is visible by default
        assert page.locator("#posNumpadContainer").is_visible(), "POS Numpad should be visible"
        assert page.locator("#inputDebtAmount").get_attribute("readonly") is not None, "Input should be readonly with POS Numpad active"

        # Press POS keys: 2, 5, 0, 000
        page.locator('.pos-key[data-key="2"]').click()
        page.locator('.pos-key[data-key="5"]').click()
        page.locator('.pos-key[data-key="0"]').click()
        page.locator('.pos-key[data-key="000"]').click()

        amount_val = page.locator("#inputDebtAmount").input_value()
        print(f"Input value after 2-5-0-000: {amount_val}")
        assert amount_val == "250000", f"Expected 250000, got {amount_val}"
        preview_text = page.locator("#amountFormattedPreview").inner_text()
        print(f"Formatted preview text: {preview_text}")
        assert clean_num(preview_text) == "250000", f"Expected clean 250000, got {preview_text}"

        # Press Backspace
        page.locator('.pos-key[data-key="backspace"]').click()
        amount_val_bs = page.locator("#inputDebtAmount").input_value()
        print(f"Input value after backspace: {amount_val_bs}")
        assert amount_val_bs == "25000"

        # Press +10k
        page.locator('.pos-key[data-key="+10k"]').click()
        amount_val_plus = page.locator("#inputDebtAmount").input_value()
        print(f"Input value after +10k: {amount_val_plus}")
        assert amount_val_plus == "35000"

        # Take screenshot of POS Numpad in action
        page.screenshot(path=os.path.join(artifact_dir, "qarz_pos_numpad.png"))
        print("Captured: qarz_pos_numpad.png")

        # Test Numpad toggle to native keyboard
        page.locator("#btnTogglePosNumpad").click()
        assert not page.locator("#posNumpadContainer").is_visible()
        assert page.locator("#inputDebtAmount").get_attribute("readonly") is None
        print("Toggled to native keyboard successfully")

        # Toggle back to POS Numpad
        page.locator("#btnTogglePosNumpad").click()
        assert page.locator("#posNumpadContainer").is_visible()

        # --- 3. Test Undo Snackbar Flow ---
        print("\n--- 3. Testing Floating Undo Snackbar Flow ---")
        # Clear amount and set 75000
        page.locator('.pos-key[data-key="clear"]').click()
        page.locator('.pos-key[data-key="7"]').click()
        page.locator('.pos-key[data-key="5"]').click()
        page.locator('.pos-key[data-key="000"]').click()

        # Fill customer: Anvar aka
        page.fill("#inputCustomerCombobox", "Anvar aka")
        # Uncheck notify checkbox so receipt modal doesn't cover snackbar
        if page.locator("#checkNotifyCustomer").is_checked():
            page.locator("#checkNotifyCustomer").uncheck()

        page.click("#formAddDebt button[type='submit']")

        # Check that Undo Snackbar appears
        page.wait_for_selector("#undoToastContainer", state="visible")
        undo_title = page.locator("#undoToastTitle").inner_text()
        print(f"Undo toast displayed: {undo_title}")
        assert "75" in undo_title
        assert "Anvar aka" in undo_title

        # Capture screenshot of Undo Snackbar (wait for slide-up animation to complete)
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(artifact_dir, "qarz_undo_toast.png"))
        print("Captured: qarz_undo_toast.png")

        # Check that total debt increased
        intermediate_debt = page.locator("#totalDebtDisplay").inner_text()
        print(f"Total debt after adding 75,000: {intermediate_debt}")
        assert clean_num(intermediate_debt) == str(int(initial_debt_num) + 75000)

        # Click Undo Button!
        page.click("#btnUndoAction")
        page.wait_for_timeout(400)

        # Check that toast hidden and debt rolled back
        assert not page.locator("#undoToastContainer").is_visible()
        rolled_back_debt = page.locator("#totalDebtDisplay").inner_text()
        print(f"Total debt after Undo: {rolled_back_debt}")
        assert clean_num(rolled_back_debt) == initial_debt_num, f"Expected {initial_debt_num}, got {clean_num(rolled_back_debt)}"
        print("Undo successfully rolled back the transaction!")

        # --- 4. Test Cloud Sync & Backup Modal ---
        print("\n--- 4. Testing Cloud Backup Modal ---")
        page.click("#btnOpenCloudBackup")
        page.wait_for_selector("#modalCloudBackup.open")
        assert page.locator("#cloudSyncTimestamp").is_visible()
        print(f"Cloud Backup modal opened: {page.locator('#cloudSyncTimestamp').inner_text()}")
        page.screenshot(path=os.path.join(artifact_dir, "qarz_cloud_backup.png"))
        print("Captured: qarz_cloud_backup.png")
        page.click('#modalCloudBackup [data-close="modalCloudBackup"]')

        # --- 5. Test QR Poster Modal ---
        print("\n--- 5. Testing Store Counter QR Poster Modal ---")
        page.click("#btnOpenQRPoster")
        page.wait_for_selector("#modalQRPoster.open")
        assert page.locator("#printableQRPoster").is_visible()
        assert page.locator(".poster-qr-svg").is_visible()
        poster_title = page.locator('#posterShopTitle').inner_text()
        print(f"Poster title: {poster_title}")
        page.screenshot(path=os.path.join(artifact_dir, "qarz_counter_qr_poster.png"))
        print("Captured: qarz_counter_qr_poster.png")
        page.click('#modalQRPoster [data-close="modalQRPoster"]')

        browser.close()
        print("\n🎉 ALL TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_all_improvements()
