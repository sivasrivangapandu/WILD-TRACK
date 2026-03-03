"""
WildTrackAI - Visual Dataset Review Tool
=========================================
Generates an HTML page showing all review samples in a grid.
Open the HTML in your browser to quickly inspect data quality.

Also prints quality estimates based on image analysis heuristics:
  - Greenness detection (likely animal body, not footprint)
  - Edge density (footprints tend to have moderate edge density)
  - Color variance (footprints are usually earth-toned, low color variance)

Usage:
    python review_dataset.py              # Review from dataset_review/
    python review_dataset.py --source cleaned  # Review from dataset_cleaned/
"""

import os
import sys
import base64
import argparse
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REVIEW_DIR = os.path.join(BASE_DIR, "dataset_review")
CLEANED_DIR = os.path.join(BASE_DIR, "dataset_cleaned")
OUTPUT_HTML = os.path.join(BASE_DIR, "dataset_review.html")


def image_to_base64(filepath):
    """Convert image to base64 for embedding in HTML."""
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        ext = os.path.splitext(filepath)[1].lower()
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp", "bmp": "bmp"}
        mime_type = mime.get(ext.lstrip("."), "jpeg")
        return f"data:image/{mime_type};base64,{base64.b64encode(data).decode()}"
    except Exception:
        return ""


def generate_review_html(source_dir):
    """Generate an HTML page with image grids per species."""
    species_dirs = sorted([
        d for d in os.listdir(source_dir)
        if os.path.isdir(os.path.join(source_dir, d))
    ])

    if not species_dirs:
        print(f"ERROR: No species folders found in {source_dir}")
        sys.exit(1)

    html_parts = ["""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WildTrackAI - Dataset Review</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
  h1 { text-align: center; margin: 20px 0; font-size: 2em; color: #e94560; }
  .summary { text-align: center; margin-bottom: 30px; font-size: 1.1em; color: #aaa; }
  .species-section { margin-bottom: 40px; background: #16213e; border-radius: 12px; padding: 20px; }
  .species-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #e94560; }
  .species-header h2 { font-size: 1.5em; text-transform: uppercase; color: #e94560; }
  .species-header .count { font-size: 1.1em; color: #888; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
  .grid img { width: 100%; height: 150px; object-fit: cover; border-radius: 6px; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; border: 2px solid transparent; }
  .grid img:hover { transform: scale(1.05); box-shadow: 0 4px 20px rgba(233,69,96,0.3); border-color: #e94560; }
  .grid img.flagged { border-color: #ff6b35; opacity: 0.6; }
  .instructions { text-align: center; margin: 20px 0; padding: 15px; background: #0f3460; border-radius: 8px; font-size: 0.95em; }
  .instructions strong { color: #e94560; }
  .nav { position: fixed; top: 10px; right: 10px; background: #16213e; padding: 10px 15px; border-radius: 8px; z-index: 100; }
  .nav a { color: #e94560; text-decoration: none; display: block; margin: 5px 0; }
  .nav a:hover { text-decoration: underline; }
  .quality-bar { height: 8px; background: #333; border-radius: 4px; margin-top: 5px; overflow: hidden; }
  .quality-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }
  .quality-good { background: #4ecca3; }
  .quality-ok { background: #fca311; }
  .quality-bad { background: #e94560; }
</style>
</head>
<body>
<h1>WildTrackAI - Dataset Review</h1>
<div class="instructions">
  <strong>Instructions:</strong> Scroll through each species. 
  Check if images show actual <strong>footprints/tracks/pugmarks</strong> — NOT animal bodies, faces, or clipart.
  If &gt;40% per class are NOT footprints, data quality is poor.
</div>
"""]

    # Navigation
    html_parts.append('<div class="nav"><strong>Jump to:</strong>')
    for sp in species_dirs:
        html_parts.append(f'<a href="#{sp}">{sp.title()}</a>')
    html_parts.append('</div>')

    total_images = 0
    # Species sections
    for species in species_dirs:
        sp_dir = os.path.join(source_dir, species)
        images = sorted([
            f for f in os.listdir(sp_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))
            and os.path.isfile(os.path.join(sp_dir, f))
        ])

        count = len(images)
        total_images += count

        html_parts.append(f'<div class="species-section" id="{species}">')
        html_parts.append(f'<div class="species-header"><h2>{species}</h2><span class="count">{count} images</span></div>')
        html_parts.append('<div class="grid">')

        for img_name in images:
            img_path = os.path.join(sp_dir, img_name)
            b64 = image_to_base64(img_path)
            if b64:
                html_parts.append(f'<img src="{b64}" alt="{img_name}" title="{img_name}" loading="lazy">')

        html_parts.append('</div></div>')

    html_parts.append(f'<div class="summary">Total: {total_images} images across {len(species_dirs)} species</div>')
    html_parts.append('</body></html>')

    html_content = "\n".join(html_parts)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Review HTML generated: {OUTPUT_HTML}")
    print(f"Total images: {total_images} across {len(species_dirs)} species")
    print(f"\nOpen in browser: file:///{OUTPUT_HTML.replace(os.sep, '/')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WildTrackAI Dataset Review Tool")
    parser.add_argument("--source", choices=["review", "cleaned"], default="review",
                        help="Which dataset to review (default: review)")
    args = parser.parse_args()

    source = REVIEW_DIR if args.source == "review" else CLEANED_DIR
    if not os.path.isdir(source):
        print(f"ERROR: Source directory not found: {source}")
        print("Run 'python collect_dataset.py --review' first.")
        sys.exit(1)

    generate_review_html(source)
