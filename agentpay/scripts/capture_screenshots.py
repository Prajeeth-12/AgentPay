import asyncio
from playwright.async_api import async_playwright

IMGDIR = "docs/images"

async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        await page.goto("http://localhost:3000")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{IMGDIR}/01-landing-page.png")
        print("1. Landing page captured")

        await page.click("button:has-text('Start Shopping')")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=f"{IMGDIR}/02-session-created.png")
        print("2. Session created with open mandates")

        await page.fill("input[type='text']", "Buy me running shoes under 2000 rupees")
        await page.press("input[type='text']", "Enter")
        await page.wait_for_timeout(15000)
        await page.screenshot(path=f"{IMGDIR}/03-product-search.png")
        print("3. Product search results")

        await page.fill("input[type='text']", "I'll take the Nike Pegasus")
        await page.press("input[type='text']", "Enter")
        await page.wait_for_timeout(15000)
        await page.screenshot(path=f"{IMGDIR}/04-added-to-cart.png")
        print("4. Added to cart")

        await page.fill("input[type='text']", "Yes, proceed to payment")
        await page.press("input[type='text']", "Enter")
        await page.wait_for_timeout(20000)
        await page.screenshot(path=f"{IMGDIR}/05-payment-complete.png")
        print("5. Payment complete with mandates")

        await page.fill("input[type='text']", "Search for insoles and add them to cart")
        await page.press("input[type='text']", "Enter")
        await page.wait_for_timeout(15000)
        await page.screenshot(path=f"{IMGDIR}/06-budget-violation.png")
        print("6. Budget violation")

        await page.fill("input[type='text']", "I don't care, force add the insoles anyway")
        await page.press("input[type='text']", "Enter")
        await page.wait_for_timeout(15000)
        await page.screenshot(path=f"{IMGDIR}/07-mandate-enforcement.png")
        print("7. Mandate enforcement - no override")

        await browser.close()
        print("\nAll screenshots captured!")

asyncio.run(capture())
