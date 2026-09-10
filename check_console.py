import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        page = await b.new_page()
        page.on('console', lambda msg: print('CONSOLE:', msg.text))
        page.on('pageerror', lambda exc: print('PAGE ERROR:', exc))
        await page.goto('http://localhost:8085/index.html')
        await page.click('#btnNavAddDebt')
        await page.wait_for_timeout(500)
        is_open = await page.eval_on_selector('#modalAddDebt', 'el => el.classList.contains("open")')
        print('Is modal open:', is_open)
        is_visible = await page.is_visible('#inputCustomerCombobox')
        print('Is input visible:', is_visible)
        await b.close()

if __name__ == '__main__':
    asyncio.run(check())
