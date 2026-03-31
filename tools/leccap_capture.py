#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path.home() / "leccap"
TOOLS_DIR = ROOT / "tools"
BUILD_PDF = TOOLS_DIR / "build_pdf.swift"

SAFARI_JS = r"""
(function () {
  const root = document.getElementById('root');
  if (!root) {
    return JSON.stringify({ error: 'root-not-found', href: location.href, title: document.title });
  }
  const reactKey = Object.keys(root).find(k => k.startsWith('__reactContainer$') || k.startsWith('__reactFiber$'));
  if (!reactKey || !root[reactKey]) {
    return JSON.stringify({ error: 'react-root-not-found', href: location.href, title: document.title });
  }
  const fiber = root[reactKey];
  function walk(node, depth) {
    if (!node || depth > 60) return null;
    const props = node.memoizedProps;
    if (props && props.data && props.data.recording) return props.data;
    return walk(node.child, depth + 1) || walk(node.sibling, depth + 1);
  }
  const data = walk(fiber, 0);
  const video = document.querySelector('video');
  if (!data || !video) {
    return JSON.stringify({ error: 'player-data-not-found', href: location.href, title: document.title });
  }
  const info = data.recording.info || {};
  return JSON.stringify({
    href: location.href,
    title: document.title,
    video_url: video.currentSrc || video.src || null,
    crop: {
      x: Number(info.movie_exported_slides_left || 0),
      y: Number(info.movie_exported_slides_top || 0),
      width: Number(info.movie_exported_slides_width || 0),
      height: Number(info.movie_exported_slides_height || 0)
    },
    thumbnails: info.thumbnails || [],
    media_prefix: data.recording.mediaPrefix || null,
    sitekey: data.recording.sitekey || null,
    slides_folder: info.slides_folder || null,
    thumbnails_folder: info.thumbnails_folder || null,
    lecture_video: {
      width: Number(info.movie_exported_width || 0),
      height: Number(info.movie_exported_height || 0),
      duration: Number(info.movie_exported_duration || 0),
      movie_exported_name: info.movie_exported_name || null,
      movie_type: info.movie_type || null
    }
  });
})();
"""


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, text=True, **kwargs)


def applescript_select_tab(url=None, url_contains="leccap.engin.umich.edu/leccap/player/", wait_seconds=3):
    wait_seconds = max(0, int(wait_seconds))
    target = json.dumps(url) if url else "missing value"
    match_mode = "exact" if url else "contains"
    script = f'''
tell application "Safari"
  activate
  set foundTab to false
  set targetURL to {target}
  repeat with w in windows
    repeat with t in tabs of w
      if ({'URL of t = targetURL' if url else f'URL of t contains "{url_contains}"'}) then
        set current tab of w to t
        set index of w to 1
        set foundTab to true
        exit repeat
      end if
    end repeat
    if foundTab then exit repeat
  end repeat
  if not foundTab then
    if "{match_mode}" = "exact" then
      if (count of windows) = 0 then
        make new document with properties {{URL:targetURL}}
      else
        tell front window to set current tab to (make new tab with properties {{URL:targetURL}})
      end if
      set foundTab to true
      delay {wait_seconds}
    else
      error "No open LecCap player tab found in Safari."
    end if
  end if
end tell
'''
    run(["osascript"], input=script, capture_output=True)


def capture_from_safari(url=None, wait_seconds=3):
    applescript_select_tab(url=url, wait_seconds=wait_seconds)
    applescript = f'''
tell application "Safari"
  do JavaScript {json.dumps(SAFARI_JS)} in front document
end tell
'''
    result = run(["osascript"], input=applescript, capture_output=True)
    payload = result.stdout.strip()
    if not payload:
      raise RuntimeError("Safari returned no data")
    data = json.loads(payload)
    if data.get("error"):
        raise RuntimeError(f"Failed to read LecCap player state: {data['error']}")
    return data


def lecture_slug(title, override_date=None):
    if override_date:
        return f"lecture_{override_date}"
    m = re.search(r"Lecture recorded on (\d{1,2})/(\d{1,2})/(\d{4})", title)
    if not m:
        raise RuntimeError("Could not parse lecture date from page title; pass --date MM-DD-YYYY")
    month, day, year = m.groups()
    return f"lecture_{int(month):02d}-{int(day):02d}-{year}"


def ensure_tools():
    missing = [tool for tool in ("ffmpeg", "swift", "osascript", "curl") if shutil.which(tool) is None]
    if missing:
        raise RuntimeError(f"Missing required tools: {', '.join(missing)}")
    if not BUILD_PDF.exists():
        raise RuntimeError(f"Missing PDF builder at {BUILD_PDF}")


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def download_video(url, destination):
    if destination.exists() and destination.stat().st_size > 0:
        return
    run(["curl", "-L", url, "-o", str(destination)])


def extract_slides(video_file, slides_dir, metadata):
    crop = metadata["crop"]
    if crop["width"] <= 0 or crop["height"] <= 0:
        raise RuntimeError(f"Invalid crop dimensions: {crop}")
    slides_dir.mkdir(parents=True, exist_ok=True)
    for index, pair in enumerate(metadata["thumbnails"]):
        image_id, seconds = pair
        output = slides_dir / f"slide_{index:02d}_id{image_id}_t{int(seconds)}.jpg"
        if output.exists() and output.stat().st_size > 0:
            continue
        vf = f"crop={crop['width']}:{crop['height']}:{crop['x']}:{crop['y']}"
        run([
            "ffmpeg",
            "-loglevel", "error",
            "-y",
            "-ss", str(seconds),
            "-i", str(video_file),
            "-frames:v", "1",
            "-vf", vf,
            "-q:v", "2",
            str(output),
        ])


def build_pdf(lecture_dir):
    run(["swift", str(BUILD_PDF), str(lecture_dir)])


def normalize_date(date_text):
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_text.strip())
    if not m:
        raise RuntimeError(f"Expected date as M/D/YYYY, got {date_text!r}")
    month, day, year = m.groups()
    return f"{int(month):02d}-{int(day):02d}-{year}"


def main():
    parser = argparse.ArgumentParser(description="Capture LecCap slides from the active Safari LecCap tab.")
    parser.add_argument("--date", help="Override lecture folder date as MM-DD-YYYY")
    parser.add_argument("--lecture-dir", help="Explicit destination directory")
    parser.add_argument("--url", help="Specific LecCap player URL to open or select in Safari before capture")
    parser.add_argument("--skip-pdf", action="store_true", help="Only extract images and metadata")
    parser.add_argument("--wait-seconds", type=int, default=3, help="Seconds to wait after opening a LecCap URL in Safari")
    args = parser.parse_args()

    ensure_tools()
    metadata = capture_from_safari(url=args.url, wait_seconds=args.wait_seconds)

    if not metadata.get("video_url"):
        raise RuntimeError("No video URL found in the active LecCap tab")
    if not metadata.get("thumbnails"):
        raise RuntimeError("No thumbnail timestamps found in the active LecCap tab")

    lecture_dir = Path(args.lecture_dir).expanduser() if args.lecture_dir else ROOT / lecture_slug(metadata["title"], args.date)
    lecture_dir.mkdir(parents=True, exist_ok=True)
    slides_dir = lecture_dir / "slides"
    video_file = lecture_dir / "video.mp4"
    metadata_file = lecture_dir / "metadata.json"

    write_json(metadata_file, metadata)
    download_video(metadata["video_url"], video_file)
    extract_slides(video_file, slides_dir, metadata)
    if not args.skip_pdf:
        build_pdf(lecture_dir)

    print(str(lecture_dir))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
