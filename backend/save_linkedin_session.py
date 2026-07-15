"""
One-Time LinkedIn Session Saver
================================
Run this script LOCALLY (not on the server) to log into LinkedIn manually
and save your session cookies.

Usage:
    python save_linkedin_session.py

After running:
1. A browser window will open and navigate to LinkedIn login.
2. Log in manually (enter your email, password, solve any CAPTCHA).
3. Once you see your LinkedIn feed, press ENTER in the terminal.
4. The script will save the session and print a base64 string.
5. Copy the base64 string and add it as a Render environment variable:
       Key:   LINKEDIN_AUTH_STATE
       Value: <paste the base64 string>
"""

import asyncio
import json
import base64
from playwright.async_api import async_playwright


async def main():
    print("=" * 60)
    print("  JobPulse - LinkedIn Session Saver")
    print("=" * 60)
    print("\nStarting headed browser... Please wait.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            no_viewport=True,
        )
        page = await context.new_page()

        print("\n>>> Navigating to LinkedIn login page...")
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        print("\n" + "=" * 60)
        print("  ACTION REQUIRED:")
        print("  1. Log into LinkedIn in the browser window that just opened.")
        print("  2. Complete any CAPTCHA or 2FA if prompted.")
        print("  3. Wait until you can see your LinkedIn FEED/HOME page.")
        print("  4. Come back here and press ENTER to save your session.")
        print("=" * 60)
        input("\n  Press ENTER once you are logged in and on the feed... ")

        # Save the storage state (cookies + localStorage)
        storage_state = await context.storage_state()

        await browser.close()

        # Save to file
        with open("auth_state.json", "w") as f:
            json.dump(storage_state, f)
        print("\n✅ Session saved to auth_state.json")

        # Encode to base64 for Render env variable
        state_bytes = json.dumps(storage_state).encode("utf-8")
        state_b64 = base64.b64encode(state_bytes).decode("utf-8")

        print("\n" + "=" * 60)
        print("  NEXT STEP - Add to Render Environment Variables:")
        print("=" * 60)
        print(f"\n  Key:   LINKEDIN_AUTH_STATE")
        print(f"\n  Value: {state_b64[:80]}...  (full value below)\n")

        # Save full base64 to a text file for easy copying
        with open("auth_state_b64.txt", "w") as f:
            f.write(state_b64)

        print("  ✅ Full base64 value saved to auth_state_b64.txt")
        print("     Open that file, copy ALL the content, paste into Render.")
        print("\n  After adding the env variable, redeploy your Render service.")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
