# LecCap Slide Extraction Workflow

This repository contains a reusable workflow for:

1. getting a lecture recording list from a University of Michigan Canvas-style external tool page
2. opening individual LecCap player pages in an authenticated Safari session
3. reading LecCap runtime metadata from the player
4. extracting slide images by cropping the lecture MP4 at the LecCap thumbnail timestamps
5. building a PDF from the extracted slide frames

The intended scope is:

- Canvas-hosted lecture listings that launch LecCap through LTI
- LecCap player pages where the main slide pane is rendered from a crop of the exported lecture MP4
- local, authenticated use on a Mac with Safari enabled for automation

This repo intentionally does not store credentials, private tokens, real course ids, or real LecCap URLs.

## Repo Layout

- `tools/leccap_capture.py`
  Captures one LecCap recording from an authenticated Safari tab or URL.
- `tools/leccap_batch.py`
  Runs the capture workflow over a saved lecture list JSON file.
- `tools/build_pdf.swift`
  Builds `slides.pdf` from extracted JPG slide frames.
- `examples/lecture_list.example.json`
  Example input file shape for batch mode.

## Prerequisites

- macOS
- Safari
- Safari Developer setting `Allow JavaScript from Apple Events` enabled
- `ffmpeg`
- Python 3
- Swift

Install `ffmpeg` with Homebrew if needed:

```bash
brew install ffmpeg
```

## How To Use The Workflow

### 1. Log in manually

Use Safari and complete any login needed for:

- your Canvas instance
- your LecCap instance

Example Canvas external tool page:

```text
https://canvas.example.edu/courses/COURSE_ID/external_tools/TOOL_ID
```

Example LecCap player page:

```text
https://leccap.example.edu/leccap/player/r/RECORDING_ID
```

### 2. Prepare a lecture list JSON

Create a local lecture list file shaped like `examples/lecture_list.example.json`.

Each entry needs:

- `date`: the lecture date in `M/D/YYYY`
- `url`: the LecCap player URL

Example:

```json
[
  {
    "date": "1/12/2026",
    "url": "https://leccap.example.edu/leccap/player/r/EXAMPLE_RECORDING_01"
  }
]
```

### 3. Capture one lecture

Run:

```bash
python3 tools/leccap_capture.py \
  --url "https://leccap.example.edu/leccap/player/r/EXAMPLE_RECORDING_01" \
  --date 01-12-2026
```

This creates a folder like:

```text
~/leccap/lecture_01-12-2026
```

Outputs:

- `metadata.json`
- `video.mp4`
- `slides/`
- `slides.pdf`

### 4. Capture a batch of lectures

Run:

```bash
python3 tools/leccap_batch.py --list-file /path/to/lecture_list.json
```

By default it skips any lecture folder that already has `slides.pdf`.

To force reprocessing:

```bash
python3 tools/leccap_batch.py --list-file /path/to/lecture_list.json --force
```

## How To Reproduce The Whole Process

### One-Shot

If you want to recreate this repository in one pass, the most precise prompt is something like:

```bash
codex "Build a local reusable workflow repo at ~/leccap for extracting slide PDFs from LecCap lecture recordings launched from a University-of-Michigan-style Canvas external tool page. Use macOS Safari as the authenticated browser and assume the user will manually log in first. Implement only reusable workflow code and documentation; do not store credentials, private tokens, real course ids, or real LecCap URLs in tracked files.

Requirements:
- Create a publishable repo layout with:
  - tools/leccap_capture.py
  - tools/leccap_batch.py
  - tools/build_pdf.swift
  - examples/lecture_list.example.json
  - README.md
  - .gitignore
- The scope is: get LecCap lecture slide PDFs for the UMich-style system by getting the lecture list from a Canvas external tool page and analyzing the MP4 in each LecCap recording.
- The single-recording script must:
  - use Safari automation on macOS
  - open or select a LecCap player URL in Safari
  - execute JavaScript in the live LecCap page
  - extract the lecture MP4 URL, the slide crop rectangle, and the LecCap thumbnail timestamp array from runtime state
  - download the MP4 if missing
  - use ffmpeg to crop the slide region at each LecCap thumbnail timestamp into JPGs
  - build slides.pdf from those JPGs using Swift
  - write metadata.json
- The batch script must:
  - read a JSON lecture list shaped like [{\"date\":\"M/D/YYYY\",\"url\":\"https://leccap.example.edu/leccap/player/r/ID\"}]
  - create lecture folders named lecture_MM-DD-YYYY
  - skip already completed lectures unless --force is passed
- The Swift PDF builder must:
  - read all JPGs in a lecture's slides/ folder
  - emit slides.pdf
- The README must:
  - explain prerequisites
  - explain how to use the workflow
  - explain how to reproduce the whole process
  - include a short end-to-end summary of the actual process
  - avoid any real course ids, real LecCap ids, or credentials
- The .gitignore must:
  - ignore everything by default
  - whitelist only the reusable workflow files and example files
  - ignore generated lecture_* outputs and local lecture list JSON files

Implementation details:
- Assume Safari Developer settings needed for Apple Events JS are enabled.
- Use ASCII only.
- Make the code concise and pragmatic.
- Do not add extra framework code.
- Do not keep one-off manual scripts in lecture folders.
- Keep the repo ready to commit."
```

### A. Enumerate LecCap lecture URLs from Canvas

This repo does not currently ship the Canvas lecture-list enumerator as a standalone script.
The reproducible manual process is:

1. open the Canvas external tool page in Safari
2. locate the LTI launch form in the page
3. relaunch it into a top-level tab
4. extract LecCap player links and dates from the resulting LecCap listing DOM
5. save those entries into a local lecture list JSON file

The batch workflow starts from that saved lecture list file.

### B. Extract LecCap runtime metadata

`tools/leccap_capture.py`:

- opens or selects the target LecCap player URL in Safari
- runs JavaScript inside the live LecCap page
- reads:
  - the exported MP4 URL
  - the slide crop rectangle
  - the LecCap thumbnail timestamp list

### C. Extract slide images from the MP4

For each LecCap thumbnail timestamp, the script runs `ffmpeg` against the local `video.mp4` and crops the slide region:

- width
- height
- x offset
- y offset

That produces one JPG per LecCap slide-change thumbnail.

### D. Build the PDF

`tools/build_pdf.swift` reads the generated JPGs from `slides/` and writes a `slides.pdf`.

## Notes And Limits

- The current automation is aimed at LecCap recordings whose main slide pane is a crop of the combined lecture MP4.
- If a different LecCap deployment serves separate image manifests, whiteboard streams, or alternate player structures, the extraction logic will need to be extended.
- Authentication is intentionally manual. The workflow assumes Safari already has a valid session.
- Local lecture outputs are ignored by git on purpose.
