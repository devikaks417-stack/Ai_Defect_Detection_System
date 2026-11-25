import os
import subprocess
import time
from pathlib import Path

SCREENSHOTS_DIR = Path("screenshots/redesign")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

targets = [
    {
        "name": "01_dashboard_overview.png",
        "url": "http://127.0.0.1:5000/#overview",
        "window_size": "1600,1000"
    },
    {
        "name": "02_inspection_overlay.png",
        "url": "http://127.0.0.1:5000/#inspection?view=overlay",
        "window_size": "1600,1050"
    },
    {
        "name": "03_inspection_side_by_side.png",
        "url": "http://127.0.0.1:5000/#inspection?view=comparison",
        "window_size": "1600,1050"
    },
    {
        "name": "04_analytics_telemetry.png",
        "url": "http://127.0.0.1:5000/#analytics",
        "window_size": "1600,1000"
    }
]

for t in targets:
    out_file = SCREENSHOTS_DIR / t["name"]
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={t['window_size']}",
        f"--screenshot={out_file.resolve()}",
        "--virtual-time-budget=4000",
        t["url"]
    ]
    print(f"Capturing screenshot: {t['name']} from {t['url']}...")
    try:
        subprocess.run(cmd, check=True, timeout=20)
        if out_file.exists():
            print(f"  [SUCCESS] Saved {out_file} ({out_file.stat().st_size} bytes)")
        else:
            print(f"  [WARNING] Output file not found for {t['name']}")
    except Exception as e:
        print(f"  [ERROR] Failed to capture {t['name']}: {e}")

print("Screenshot capture complete.")
