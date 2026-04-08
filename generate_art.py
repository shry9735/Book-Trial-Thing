#!/usr/bin/env python3
"""
generate_art.py — Page-by-page book illustration generator.

Pipeline:
    book text (per page)
        → Ollama / llama3.1  (writes an image prompt)
        → ComfyUI / Flux.1 Schnell  (renders the image)
        → saved PNG

Usage:
    python generate_art.py Book2/story.md
    python generate_art.py Book1/chapters/
    python generate_art.py Book2/story.md --pages 1-5
    python generate_art.py Book2/story.md --dry-run
    python generate_art.py Book2/story.md --workflow my_workflow.json

Requirements:
    pip install requests

    Ollama:    https://ollama.com  →  ollama pull llama3.1
    ComfyUI:   https://github.com/comfyanonymous/ComfyUI
               + Flux.1 Schnell fp8 models (see MODEL SETUP below)

──────────────────────────────────────────────────────
MODEL SETUP (ComfyUI)
──────────────────────────────────────────────────────
Download these four files from Hugging Face
(black-forest-labs/FLUX.1-schnell and city96/FLUX.1-schnell-gguf for fp8):

  models/unet/      flux1-schnell-fp8.safetensors
  models/vae/       ae.safetensors
  models/clip/      t5xxl_fp8_e4m3fn.safetensors
  models/clip/      clip_l.safetensors

Start ComfyUI with:
  python main.py --listen --lowvram

The --lowvram flag lets your 128 GB of RAM absorb what doesn't fit in VRAM.

──────────────────────────────────────────────────────
CUSTOM WORKFLOW
──────────────────────────────────────────────────────
If you want to use your own workflow:
  1. In ComfyUI: Settings → Enable Dev Mode Options → "Save (API Format)"
  2. Save the file, then pass it here: --workflow my_workflow.json
  The script will find your CLIPTextEncode node and inject the prompt.
"""

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

import requests

# ── Configuration ──────────────────────────────────────────────────────────────

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1"          # change to e.g. "mistral" if you prefer

COMFYUI_URL  = "http://localhost:8188"

# Art style injected at the start of every image prompt.
# Tweak this to change the overall look of all illustrations.
STYLE_PREFIX = (
    "children's book illustration, flat vector art, bright warm colours, "
    "clean bold line art, friendly and inviting, digital art, "
    "no text, no words"
)

# Ollama system prompt that turns page text into an image prompt
OLLAMA_SYSTEM = """\
You are an art director creating illustration briefs for a children's book aimed at 10-year-olds.

Given a page of text, write ONE concise image prompt (max 60 words) that:
- Describes the key visual moment on the page
- Names any characters present (Spark = boy with dark curly hair; Bitsy = girl with braids; D.U.D.E.A.D. = small wheeled robot with LCD screen)
- Specifies the setting and mood
- Avoids narrative spoilers
- Does NOT include style words (those are added automatically)

Reply with ONLY the image prompt. No preamble, no explanation."""

# ── Default ComfyUI workflow (Flux.1 Schnell fp8) ─────────────────────────────
# Matches the standard model filenames from Hugging Face.
# Override with --workflow if your filenames differ.

DEFAULT_WORKFLOW = {
    "6": {
        "inputs": {
            "text": "PROMPT_PLACEHOLDER",
            "clip": ["11", 0]
        },
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Positive Prompt"}
    },
    "8": {
        "inputs": {
            "samples": ["13", 0],
            "vae": ["10", 0]
        },
        "class_type": "VAEDecode"
    },
    "9": {
        "inputs": {
            "filename_prefix": "bookart",
            "images": ["8", 0]
        },
        "class_type": "SaveImage"
    },
    "10": {
        "inputs": {"vae_name": "ae.safetensors"},
        "class_type": "VAELoader"
    },
    "11": {
        "inputs": {
            "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
            "clip_name2": "clip_l.safetensors",
            "type": "flux"
        },
        "class_type": "DualCLIPLoader"
    },
    "12": {
        "inputs": {
            "unet_name": "flux1-schnell-fp8.safetensors",
            "weight_dtype": "fp8_e4m3fn"
        },
        "class_type": "UNETLoader"
    },
    "13": {
        "inputs": {
            "noise":         ["25", 0],
            "guider":        ["22", 0],
            "sampler":       ["16", 0],
            "sigmas":        ["17", 0],
            "latent_image":  ["27", 0]
        },
        "class_type": "SamplerCustomAdvanced"
    },
    "16": {
        "inputs": {"sampler_name": "euler"},
        "class_type": "KSamplerSelect"
    },
    "17": {
        "inputs": {
            "model":      ["12", 0],
            "scheduler":  "simple",
            "steps":      4,
            "denoise":    1.0,
            "guidance":   3.5,
            "max_shift":  1.15,
            "base_shift": 0.5
        },
        "class_type": "BasicScheduler"
    },
    "22": {
        "inputs": {
            "model":        ["12", 0],
            "conditioning": ["6", 0]
        },
        "class_type": "BasicGuider"
    },
    "25": {
        "inputs": {"noise_seed": 42},
        "class_type": "RandomNoise"
    },
    "27": {
        "inputs": {
            "width":      768,
            "height":     1024,
            "batch_size": 1
        },
        "class_type": "EmptySD3LatentImage"
    }
}

# ── Book parsing ───────────────────────────────────────────────────────────────

def parse_markdown_book(path: Path) -> list[tuple[str, str]]:
    """
    Split a markdown file on '## Page N' headings.
    Returns [(label, text), ...] e.g. [("page_01", "Saturday morning..."), ...]
    Also captures a 'front' section before the first page heading.
    """
    text = path.read_text(encoding="utf-8")
    # Split on ## Page N  (case-insensitive, optional whitespace)
    parts = re.split(r"(?m)^##\s+Page\s+(\d+)\s*$", text)

    pages = []

    # parts[0] is content before first ## Page — treat as "front matter"
    front = parts[0].strip()
    if front:
        pages.append(("front", front))

    # parts then alternates: number, content, number, content, ...
    for i in range(1, len(parts), 2):
        num  = int(parts[i])
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if body:
            pages.append((f"page_{num:03d}", body))

    return pages


def parse_html_dir(path: Path) -> list[tuple[str, str]]:
    """
    Treat each HTML file in a directory as one 'page' (chapter).
    Strips HTML tags so Ollama gets plain text.
    """
    pages = []
    for html_file in sorted(path.glob("*.html")):
        raw  = html_file.read_text(encoding="utf-8", errors="replace")
        # Strip style/script blocks first
        raw  = re.sub(r"(?si)<style[^>]*>.*?</style>", " ", raw)
        raw  = re.sub(r"(?si)<script[^>]*>.*?</script>", " ", raw)
        # Strip remaining tags
        text = re.sub(r"<[^>]+>", " ", raw)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        label = re.sub(r"[^\w]+", "_", html_file.stem.lower()).strip("_")
        pages.append((label, text))
    return pages


def load_pages(input_path: Path) -> list[tuple[str, str]]:
    if input_path.is_dir():
        return parse_html_dir(input_path)
    suffix = input_path.suffix.lower()
    if suffix in (".md", ".markdown"):
        return parse_markdown_book(input_path)
    sys.exit(f"Unsupported input: {input_path}  (pass a .md file or a directory of .html files)")


# ── Page range filtering ───────────────────────────────────────────────────────

def parse_page_filter(spec: str) -> set[int]:
    """
    Parse a page filter like "1,3,5-10" into a set of page numbers.
    Only meaningful for markdown books where labels are page_NNN.
    """
    nums: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            nums.update(range(int(m.group(1)), int(m.group(2)) + 1))
        elif re.fullmatch(r"\d+", part):
            nums.add(int(part))
        else:
            sys.exit(f"Invalid page filter token: '{part}'  (expected e.g. '1-5,8,12')")
    return nums


def label_to_page_num(label: str) -> int | None:
    m = re.search(r"(\d+)$", label)
    return int(m.group(1)) if m else None


# ── Ollama ─────────────────────────────────────────────────────────────────────

def generate_prompt(page_text: str, timeout: int = 60) -> str:
    """Call Ollama to turn page text into an image prompt."""
    # Trim very long pages — Ollama only needs the gist
    excerpt = page_text[:2000]

    payload = {
        "model":  OLLAMA_MODEL,
        "system": OLLAMA_SYSTEM,
        "prompt": excerpt,
        "stream": False,
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        sys.exit(
            "\nCannot reach Ollama at localhost:11434.\n"
            "Start it with:  ollama serve\n"
            "Then pull the model:  ollama pull llama3.1"
        )

    data = resp.json()
    prompt = data.get("response", "").strip()
    if not prompt:
        raise RuntimeError(f"Ollama returned empty response: {data}")
    return prompt


# ── ComfyUI ────────────────────────────────────────────────────────────────────

def inject_prompt(workflow: dict, image_prompt: str) -> dict:
    """
    Deep-copy the workflow and replace the text in any CLIPTextEncode node.
    If multiple exist (positive + negative), replaces the one with the
    longest existing text (most likely the positive prompt).
    """
    import copy
    wf = copy.deepcopy(workflow)

    candidates = [
        (node_id, node)
        for node_id, node in wf.items()
        if node.get("class_type") == "CLIPTextEncode"
    ]

    if not candidates:
        raise RuntimeError("No CLIPTextEncode node found in workflow.")

    # Pick the node with the longest current text (positive prompt heuristic)
    target_id = max(candidates, key=lambda x: len(x[1]["inputs"].get("text", "")))[0]
    wf[target_id]["inputs"]["text"] = image_prompt

    return wf


def randomise_seed(workflow: dict) -> dict:
    """Set a random seed in any RandomNoise or KSampler node."""
    for node in workflow.values():
        ct = node.get("class_type", "")
        if ct == "RandomNoise":
            node["inputs"]["noise_seed"] = random.randint(0, 2**32 - 1)
        elif ct == "KSampler":
            node["inputs"]["seed"] = random.randint(0, 2**32 - 1)
    return workflow


def submit_to_comfyui(workflow: dict) -> str:
    """POST the workflow and return the prompt_id."""
    payload = {
        "prompt":    workflow,
        "client_id": "generate_art_script",
    }
    try:
        resp = requests.post(f"{COMFYUI_URL}/prompt", json=payload, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        sys.exit(
            "\nCannot reach ComfyUI at localhost:8188.\n"
            "Start it with:  python main.py --listen --lowvram"
        )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"ComfyUI rejected workflow: {data['error']}")
    return data["prompt_id"]


def wait_for_completion(prompt_id: str, poll_interval: float = 2.0, timeout: int = 600) -> dict:
    """Poll /history until the prompt is done, then return the output data."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
        resp.raise_for_status()
        history = resp.json()
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(poll_interval)
    raise TimeoutError(f"ComfyUI did not finish prompt {prompt_id} within {timeout}s")


def fetch_image(filename: str, subfolder: str = "", img_type: str = "output") -> bytes:
    """Download a generated image from ComfyUI's /view endpoint."""
    params = {"filename": filename, "type": img_type}
    if subfolder:
        params["subfolder"] = subfolder
    resp = requests.get(f"{COMFYUI_URL}/view", params=params, timeout=60)
    resp.raise_for_status()
    return resp.content


def generate_image(workflow: dict, image_prompt: str) -> bytes:
    """Full round-trip: inject prompt → submit → wait → fetch → return PNG bytes."""
    wf = inject_prompt(workflow, image_prompt)
    wf = randomise_seed(wf)

    prompt_id = submit_to_comfyui(wf)

    result = wait_for_completion(prompt_id)

    # Find the SaveImage output
    outputs = result.get("outputs", {})
    for node_output in outputs.values():
        images = node_output.get("images", [])
        if images:
            img_info = images[0]
            return fetch_image(
                img_info["filename"],
                img_info.get("subfolder", ""),
                img_info.get("type", "output"),
            )

    raise RuntimeError(f"No image found in ComfyUI output for prompt {prompt_id}.\nOutputs: {outputs}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate page-by-page illustrations for your books.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        help="Path to a .md book file OR a directory of .html chapter files.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        help="Where to save images (default: <input_dir>/art/).",
    )
    parser.add_argument(
        "--pages",
        help="Only generate specific pages, e.g. '1-5,8,12' (markdown books only).",
    )
    parser.add_argument(
        "--workflow",
        help="Path to a ComfyUI API-format workflow JSON (overrides built-in default).",
    )
    parser.add_argument(
        "--model",
        default=OLLAMA_MODEL,
        help=f"Ollama model to use for prompt generation (default: {OLLAMA_MODEL}).",
    )
    parser.add_argument(
        "--style",
        default=STYLE_PREFIX,
        help="Style prefix prepended to every image prompt.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse the book and print what would be generated without calling any API.",
    )
    parser.add_argument(
        "--prompts-only",
        action="store_true",
        help="Call Ollama to generate prompts but stop before calling ComfyUI.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip pages that already have a saved image (default: on).",
    )
    parser.add_argument(
        "--no-skip-existing",
        dest="skip_existing",
        action="store_false",
        help="Re-generate images even if they already exist.",
    )
    args = parser.parse_args()

    # ── Load workflow ──
    if args.workflow:
        wf_path = Path(args.workflow)
        if not wf_path.is_file():
            sys.exit(f"Workflow file not found: {wf_path}")
        workflow = json.loads(wf_path.read_text())
        print(f"Using workflow: {wf_path}")
    else:
        workflow = DEFAULT_WORKFLOW
        print("Using built-in Flux.1 Schnell workflow.")

    # ── Load pages ──
    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"Input not found: {input_path}")

    pages = load_pages(input_path)
    if not pages:
        sys.exit("No pages found in input.")

    print(f"Found {len(pages)} page(s) in {input_path.name}")

    # ── Apply page filter ──
    if args.pages:
        page_filter = parse_page_filter(args.pages)
        pages = [
            (label, text) for (label, text) in pages
            if (n := label_to_page_num(label)) is not None and n in page_filter
        ]
        print(f"Filtered to {len(pages)} page(s) matching --pages {args.pages}")

    # ── Output directory ──
    if args.output_dir:
        out_dir = Path(args.output_dir)
    elif input_path.is_dir():
        out_dir = input_path / "art"
    else:
        out_dir = input_path.parent / "art"

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"Saving images to: {out_dir}/\n")

    # ── Generate ──
    style = args.style

    for i, (label, page_text) in enumerate(pages, 1):
        out_path = out_dir / f"{label}.png"
        prefix = f"[{i}/{len(pages)}] {label}"

        if args.skip_existing and not args.dry_run and out_path.exists():
            print(f"{prefix} — skipped (already exists)")
            continue

        if args.dry_run:
            # Show first 120 chars of the page
            preview = page_text[:120].replace("\n", " ")
            print(f"{prefix} — DRY RUN — '{preview}…'")
            continue

        # Step 1: generate image prompt via Ollama
        print(f"{prefix} — generating prompt…", end=" ", flush=True)
        try:
            raw_prompt = generate_prompt(page_text)
        except Exception as e:
            print(f"FAILED (Ollama): {e}")
            continue
        full_prompt = f"{style}, {raw_prompt}"
        print(f"OK\n           prompt: {full_prompt[:100]}…")

        if args.prompts_only:
            print(f"           (--prompts-only: skipping image generation)")
            continue

        # Step 2: generate image via ComfyUI
        print(f"           rendering image…", end=" ", flush=True)
        try:
            image_bytes = generate_image(workflow, full_prompt)
        except Exception as e:
            print(f"FAILED (ComfyUI): {e}")
            continue

        # Step 3: save
        out_path.write_bytes(image_bytes)
        size_kb = len(image_bytes) // 1024
        print(f"OK — saved {out_path.name} ({size_kb} KB)")

    print("\nDone.")


if __name__ == "__main__":
    main()
