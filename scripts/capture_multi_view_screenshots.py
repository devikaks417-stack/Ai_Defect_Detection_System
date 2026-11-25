import subprocess
import time
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = Path("screenshots/frontend")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CAPTURES = [
    {
        "url": "http://127.0.0.1:5000/#analytics",
        "width": 1440,
        "height": 950,
        "filename": "analytics_page.png",
        "delay": 2.5
    },
    {
        "url": "http://127.0.0.1:5000/#inspection?view=original",
        "width": 1440,
        "height": 950,
        "filename": "view1_original.png",
        "delay": 3.0
    },
    {
        "url": "http://127.0.0.1:5000/#inspection?view=heatmap",
        "width": 1440,
        "height": 950,
        "filename": "view2_heatmap.png",
        "delay": 3.0
    },
    {
        "url": "http://127.0.0.1:5000/#inspection?view=overlay",
        "width": 1440,
        "height": 950,
        "filename": "view3_overlay.png",
        "delay": 3.0
    },
    {
        "url": "http://127.0.0.1:5000/#inspection?view=comparison",
        "width": 1440,
        "height": 950,
        "filename": "view4_side_by_side.png",
        "delay": 3.0
    }
]

def capture_all():
    print("Capturing Multi-View and Analytics Screenshots...")
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
