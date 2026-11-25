import subprocess
import time
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = Path("screenshots/frontend")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CAPTURES = [
    {
        "url": "http://127.0.0.1:5000/",
        "width": 1440,
        "height": 900,
        "filename": "desktop_overview.png",
        "delay": 2.5
    },
    {
        "url": "http://127.0.0.1:5000/#inspection",
        "width": 1440,
        "height": 900,
        "filename": "desktop_inspection.png",
        "delay": 3.5
    },
    {
        "url": "http://127.0.0.1:5000/",
        "width": 768,
        "height": 1024,
        "filename": "tablet_overview.png",
        "delay": 2.5
    },
    {
        "url": "http://127.0.0.1:5000/",
        "width": 390,
        "height": 844,
        "filename": "mobile_overview.png",
        "delay": 2.5
    },
    {
        "url": "http://127.0.0.1:5000/#inspection",
        "width": 390,
        "height": 844,
        "filename": "mobile_inspection.png",
        "delay": 3.5
    }
]

def capture_all():
    print("Capturing Enterprise Frontend Screenshots...")
    for cap in CAPTURES:
        out_file = OUTPUT_DIR / cap["filename"]
        print(f"Capturing {cap['filename']} ({cap['width']}x{cap['height']}) ...")
        
        cmd = [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={cap['width']},{cap['height']}",
            f"--screenshot={out_file.resolve()}",
            f"--virtual-time-budget={int(cap['delay'] * 1000)}",
            cap["url"]
        ]
        
        res = subprocess.run(cmd, capture_output=True, timeout=30)
        if out_file.exists():
            print(f"  [SUCCESS] Written {out_file.name} ({out_file.stat().st_size} bytes)")
        else:
            print(f"  [ERROR] Failed to write {out_file.name}: {res.stderr.decode('utf-8', errors='ignore')}")

if __name__ == "__main__":
    capture_all()
