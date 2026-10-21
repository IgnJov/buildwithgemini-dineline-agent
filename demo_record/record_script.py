import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--window-size=1280,800",
                "--window-position=0,0",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir="/config/Desktop/BuildWithGemini/dineline-agent/demo_record/videos",
            record_video_size={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        print("Navigating to live frontend...")
        page.goto("https://dineline-frontend-rdp6fp2xga-ue.a.run.app")
        page.wait_for_selector("#input")
        time.sleep(2)
        
        # Prompt 1: What DineLine AI does best - Natural Language Waitlist & Queue Check-in
        prompt_1 = "Hi! We have a party of 4 under Sarah Miller, and we would love a patio booth if available."
        print(f"Typing Prompt 1: {prompt_1}")
        page.fill("#input", "")
        for char in prompt_1:
            page.type("#input", char, delay=35)
            time.sleep(0.01)
        
        time.sleep(1)
        page.click("button")
        print("Sent Prompt 1, waiting for agent response...")
        
        # Wait for agent response
        page.wait_for_selector(".msg.agent", timeout=120000)
        time.sleep(8)
        
        # Prompt 2: Rich query showing off Firestore database lookup & dietary filtering
        prompt_2 = "Can you check your menu for gluten-free main dishes with prices and ingredients?"
        print(f"Typing Prompt 2: {prompt_2}")
        page.fill("#input", "")
        for char in prompt_2:
            page.type("#input", char, delay=35)
            time.sleep(0.01)
            
        time.sleep(1)
        page.click("button")
        print("Sent Prompt 2, waiting for agent response...")
        
        # Wait for second agent response
        page.wait_for_function("document.querySelectorAll('.msg.agent').length >= 2", timeout=120000)
        time.sleep(10)
        
        print("Demo interaction completed. Closing browser and finalizing video...")
        context.close()
        browser.close()

if __name__ == "__main__":
    run()
