"""
PDF and Screenshot Generation Module
Uses Playwright to capture high-quality PDF or PNG screenshots of HTML reports.
"""
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

async def capture_screenshot(source_html: str, target_file: str):
    """
    Render HTML to PDF or Image via headless browser
    Args:
        source_html: Input HTML path
        target_file: Output file path (.pdf or .png)
    """
    if not os.path.exists(source_html):
        print(f"❌ Source missing: {source_html}")
        return
        
    async with async_playwright() as pw:
        # Browser setup
        engine = await pw.chromium.launch()
        view = await engine.new_context(
            viewport={'width': 480, 'height': 800},
            device_scale_factor=2
        )
        
        tab = await view.new_page()
        local_url = f"file://{os.path.abspath(source_html)}"
        
        # Load and wait
        await tab.goto(local_url)
        await tab.wait_for_load_state("networkidle")
        await asyncio.sleep(1.5) # Font rendering buffer
        
        # Auto-height adjustment
        doc_height = await tab.evaluate("document.body.scrollHeight")
        await tab.set_viewport_size({'width': 480, 'height': doc_height})
        
        # Ensure directory
        Path(target_file).parent.mkdir(parents=True, exist_ok=True)
        
        if target_file.lower().endswith('.pdf'):
            await tab.pdf(
                path=target_file,
                width="480px",
                height=f"{doc_height}px",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
            )
            print(f"✅ PDF created: {target_file}")
        else:
            await tab.screenshot(path=target_file, full_page=True)
            print(f"✅ Image created: {target_file}")
            
        await engine.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        asyncio.run(capture_screenshot(sys.argv[1], sys.argv[2]))
