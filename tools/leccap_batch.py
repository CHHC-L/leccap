#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path.home() / "leccap"
TOOLS_DIR = ROOT / "tools"
CAPTURE = TOOLS_DIR / "leccap_capture.py"


def run(cmd):
    return subprocess.run(cmd, check=True, text=True)


def normalize_date(date_text):
    month, day, year = [part.strip() for part in date_text.split("/")]
    return f"{int(month):02d}-{int(day):02d}-{year}"


def lecture_dir_for(date_text):
    return ROOT / f"lecture_{normalize_date(date_text)}"


def main():
    parser = argparse.ArgumentParser(description="Batch-capture LecCap slide decks from a saved lecture list.")
    parser.add_argument("--list-file", default=str(ROOT / "lecture_list_winter_2026.json"))
    parser.add_argument("--force", action="store_true", help="Re-run capture even if slides.pdf already exists")
    parser.add_argument("--wait-seconds", type=int, default=4)
    args = parser.parse_args()

    lectures = json.loads(Path(args.list_file).read_text())
    for item in lectures:
        date_text = item["date"]
        url = item["url"]
        lecture_dir = lecture_dir_for(date_text)
        pdf_path = lecture_dir / "slides.pdf"
        if pdf_path.exists() and not args.force:
            print(f"skip {date_text} {url}")
            continue
        cmd = [
            sys.executable,
            str(CAPTURE),
            "--url", url,
            "--date", normalize_date(date_text),
            "--wait-seconds", str(args.wait_seconds),
        ]
        print(f"capture {date_text} {url}")
        run(cmd)


if __name__ == "__main__":
    main()
