"""
3D Model Generator API — Ollama Edition
Replaces Groq with locally-hosted Ollama models.

Models:
  - Text-to-3D: glm4 (or mistral as fallback)
  - Image-to-3D: llama3.2-vision
  - All via Ollama OpenAI-compatible API at localhost:11434

Follows Hermes OS Constitution Article 4: "Prefer local models over paid APIs."
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import asyncio
import base64
import glob
import httpx
import os
import re
import subprocess

load_dotenv()

# ─── Ollama Client (OpenAI-compatible) ───────────────────────────
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "ollama")
TEXT_MODEL = os.environ.get("OLLAMA_TEXT_MODEL", "glm4")
VISION_MODEL = os.environ.get("OLLAMA_VISION_MODEL", "llama3.2-vision")

# HuggingFace token — used for both HF Spaces and Inference API (free, optional).
# Defined here (early) so vision functions can use it.
HF_TOKEN = os.environ.get("HF_TOKEN", "")

ollama_client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)

# ─── OpenSCAD binary path ────────────────────────────────────────
def find_openscad():
    """Find openscad binary — works on Linux (Docker) and Windows (local)."""
    # Check common Windows path
    win_path = os.path.expanduser("~/openscad/openscad-2021.01/openscad.exe")
    if os.path.exists(win_path):
        return win_path
    # Check PATH
    import shutil
    if shutil.which("openscad"):
        return "openscad"
    # Linux/Docker default
    if os.path.exists("/usr/bin/openscad"):
        return "openscad"
    return "openscad"

OPENSCAD_BIN = find_openscad()

# ─── Shape Library ───────────────────────────────────────────────
SHAPES = {
    "chair": """union() {
  translate([0,0,12]) cube([40,40,4], center=true);
  translate([-16,-16,0]) cylinder(h=12, r=2);
  translate([16,-16,0]) cylinder(h=12, r=2);
  translate([-16,16,0]) cylinder(h=12, r=2);
  translate([16,16,0]) cylinder(h=12, r=2);
  translate([0,18,18]) cube([40,4,12], center=true);
}""",
    "table": """union() {
  translate([0,0,25]) cube([60,60,4], center=true);
  translate([-25,-25,0]) cylinder(h=25, r=3);
  translate([25,-25,0]) cylinder(h=25, r=3);
  translate([-25,25,0]) cylinder(h=25, r=3);
  translate([25,25,0]) cylinder(h=25, r=3);
}""",
    "house": """union() {
  cube([40,40,30], center=true);
  translate([0,0,25]) cylinder(h=20, r1=30, r2=0, $fn=4);
}""",
    "snowman": """union() {
  sphere(r=10);
  translate([0,0,18]) sphere(r=7);
  translate([0,0,28]) sphere(r=5);
}""",
    "rocket": """union() {
  cylinder(h=40, r=5);
  translate([0,0,40]) cylinder(h=15, r1=5, r2=0);
  translate([5,0,0]) rotate([0,30,0]) cylinder(h=15, r=1);
  translate([-5,0,0]) rotate([0,-30,0]) cylinder(h=15, r=1);
}""",
    "box": """cube([30,20,10], center=true);""",
    "sphere": """sphere(r=20);""",
    "cylinder": """cylinder(h=30, r=10);""",
    "cone": """cylinder(h=30, r1=15, r2=0);""",
    "mushroom": """union() {
  cylinder(h=20, r=5);
  translate([0,0,25]) sphere(r=18);
}""",
    "trophy": """union() {
  cylinder(h=5, r=15);
  translate([0,0,8]) cylinder(h=20, r=8);
  translate([0,0,31]) sphere(r=8);
}""",
    "cat": """union() {
  sphere(r=10);
  translate([0,0,14]) sphere(r=8);
  translate([-4,0,22]) cylinder(h=6, r1=3, r2=1);
  translate([4,0,22]) cylinder(h=6, r1=3, r2=1);
  translate([15,0,8]) rotate([0,90,0]) cylinder(h=10, r=2);
}""",
    "tree": """union() {
  cylinder(h=15, r=3);
  translate([0,0,15]) cylinder(h=20, r1=15, r2=0);
  translate([0,0,25]) cylinder(h=20, r1=12, r2=0);
  translate([0,0,35]) cylinder(h=15, r1=8, r2=0);
}""",
    "car": """union() {
  cube([60,25,15], center=true);
  translate([0,0,10]) cube([35,22,12], center=true);
  translate([-18,-15,0]) cylinder(h=5, r=8);
  translate([18,-15,0]) cylinder(h=5, r=8);
  translate([-18,15,0]) cylinder(h=5, r=8);
  translate([18,15,0]) cylinder(h=5, r=8);
}""",
    "bottle": """union() {
  cylinder(h=30, r=10);
  translate([0,0,30]) cylinder(h=15, r1=10, r2=4);
  translate([0,0,45]) cylinder(h=10, r=4);
}""",
    "pyramid": """cylinder(h=15, r1=10, r2=0, $fn=4);""",
    "ring": """rotate_extrude($fn=50) translate([8,0,0]) circle(r=2, $fn=20);""",
    "phone": """union() {
  cube([8,16,1], center=true);
  translate([0,0,0.5]) cube([6,12,0.5], center=true);
}""",
    "bat": """union() {
  cylinder(h=20, r=2);
  translate([0,0,18]) sphere(r=4);
}""",
    "star": """cylinder(h=2, r=8, $fn=5);""",
    "heart": """union() {
  translate([3,0,0]) cylinder(h=5, r=4);
  translate([-3,0,0]) cylinder(h=5, r=4);
  translate([0,-4,0]) cube([8,6,5]);
}""",
    "bridge": """union() {
  translate([0,0,0]) cube([80,10,5], center=true);
  translate([0,0,15]) difference() {
    cylinder(h=20, r=40, $fn=40);
    cylinder(h=20, r=35, $fn=40);
  }
  translate([-35,0,0]) cylinder(h=10, r=3);
  translate([35,0,0]) cylinder(h=10, r=3);
}""",
    "tower": """union() {
  cylinder(h=50, r=10);
  translate([0,0,50]) cylinder(h=5, r1=10, r2=14);
  translate([0,0,55]) cylinder(h=3, r=14);
  translate([0,0,58]) cylinder(h=15, r1=2, r2=2);
  translate([0,0,73]) sphere(r=3);
}""",
    "windmill": """union() {
  cylinder(h=40, r=6);
  translate([0,0,40]) cylinder(h=5, r=8);
  translate([0,0,45]) rotate([90,0,0]) cylinder(h=30, r=2, center=true);
  translate([0,0,45]) rotate([0,90,0]) cylinder(h=30, r=2, center=true);
  translate([0,0,45]) sphere(r=4);
}""",
    "guitar": """union() {
  translate([0,0,0]) cylinder(h=8, r=15);
  translate([0,0,8]) cylinder(h=8, r=12);
  translate([0,0,16]) cylinder(h=40, r=3);
  translate([0,0,56]) cylinder(h=10, r=5);
}""",
    "cup": """difference() {
  union() {
    cylinder(h=30, r=10);
    translate([12,0,20]) rotate([0,90,0]) cylinder(h=8, r=3, center=true);
  }
  translate([0,0,3]) cylinder(h=28, r=8);
}""",
    "donut": """rotate_extrude($fn=50) translate([12,0,0]) circle(r=4, $fn=30);""",
    "diamond": """union() {
  cylinder(h=10, r1=12, r2=4);
  translate([0,0,10]) cylinder(h=10, r1=4, r2=12);
  translate([0,0,-5]) cylinder(h=5, r1=14, r2=12);
}""",
    "hammer": """union() {
  translate([0,0,0]) cube([5,5,30], center=true);
  translate([0,0,15]) cube([25,8,8], center=true);
  translate([10,0,15]) cube([10,12,12], center=true);
}""",
    "key": """union() {
  translate([0,0,0]) cylinder(h=3, r=8, $fn=30);
  translate([0,0,3]) cylinder(h=3, r=5, $fn=30);
  translate([0,0,1.5]) cylinder(h=3, r=3, $fn=30);
  translate([0,0,6]) cube([3,25,3], center=true);
  translate([0,20,6]) cube([3,3,8]);
  translate([0,15,6]) cube([3,3,8]);
}""",
    "gear": """union() {
  difference() {
    union() {
      cylinder(h=5, r=15, $fn=20);
      for(i=[0:60:300]) rotate([0,0,i]) translate([17,0,0]) cube([6,5,5], center=true);
    }
    cylinder(h=6, r=4, center=true);
  }
}""",
    "lamp": """union() {
  cylinder(h=30, r=2);
  translate([0,0,30]) cylinder(h=3, r1=2, r2=10);
  translate([0,0,33]) cylinder(h=8, r1=10, r2=12);
  translate([0,0,41]) cylinder(h=1, r=12);
}""",
    "fish": """union() {
  translate([0,0,0]) sphere(r=12);
  translate([-18,0,0]) rotate([0,0,30]) cube([12,4,10], center=true);
  translate([-18,0,5]) rotate([0,0,-30]) cube([12,4,10], center=true);
  translate([10,0,0]) sphere(r=6);
  translate([14,3,3]) sphere(r=1);
  translate([14,3,-3]) sphere(r=1);
}""",
    "flower": """union() {
  cylinder(h=30, r=2);
  translate([0,0,30]) for(i=[0:72:288]) rotate([0,0,i]) translate([8,0,0]) sphere(r=6);
  translate([0,0,30]) sphere(r=4);
}""",
    "wheel": """union() {
  difference() {
    cylinder(h=4, r=20, $fn=40);
    cylinder(h=5, r=4, center=true);
  }
  for(i=[0:60:300]) rotate([90,0,i]) translate([0,0,0]) cube([2,18,2], center=true);
}""",
    "bolt": """union() {
  cylinder(h=30, r=5, $fn=6);
  translate([0,0,30]) cylinder(h=5, r=10, $fn=6);
}""",
    "nut": """difference() {
  cylinder(h=5, r=10, $fn=6);
  cylinder(h=6, r=4, center=true);
}""",
    "stairs": """union() {
  for(i=[0:5]) translate([0,0,i*5]) cube([30,10,5]);
  translate([0,-5,0]) cube([30,5,35]);
}""",
    "shelf": """union() {
  cube([40,10,3], center=true);
  translate([0,0,15]) cube([40,10,3], center=true);
  translate([0,0,30]) cube([40,10,3], center=true);
  translate([-18,0,15]) cube([3,10,33]);
  translate([18,0,15]) cube([3,10,33]);
}""",
    "boat": """union() {
  difference() {
    cube([50,15,10], center=true);
    translate([0,0,2]) cube([44,11,10], center=true);
  }
  translate([0,0,12]) cube([5,14,15], center=true);
}""",
    "rocket2": """union() {
  cylinder(h=40, r=8);
  translate([0,0,40]) cylinder(h=10, r1=8, r2=2);
  translate([8,0,5]) rotate([0,40,0]) cylinder(h=15, r1=3, r2=1);
  translate([-8,0,5]) rotate([0,-40,0]) cylinder(h=15, r1=3, r2=1);
  translate([0,8,5]) rotate([40,0,0]) cylinder(h=15, r1=3, r2=1);
  translate([0,-8,5]) rotate([-40,0,0]) cylinder(h=15, r1=3, r2=1);
}""",
    "anchor": """union() {
  cylinder(h=40, r=2);
  translate([0,0,40]) cylinder(h=3, r=6, $fn=30);
  translate([0,0,20]) rotate([90,0,0]) cylinder(h=20, r=3, center=true);
  translate([0,-10,10]) rotate([0,0,180]) difference() {
    cylinder(h=4, r=12, $fn=40);
    cylinder(h=5, r=8, $fn=40);
  }
}""",
    "sword": """union() {
  translate([0,0,20]) cube([3,3,40], center=true);
  translate([0,0,0]) cube([10,2,3], center=true);
  translate([0,0,-3]) cylinder(h=8, r=2);
  translate([0,0,-11]) sphere(r=3);
}""",
    "dog": """union() {
  translate([0,0,10]) cube([30,15,20], center=true);
  translate([15,0,5]) cylinder(h=15, r=5);
  translate([20,0,15]) sphere(r=5);
  translate([15,5,15]) sphere(r=1);
  translate([15,-5,15]) sphere(r=1);
  translate([-12,5,0]) cylinder(h=8, r=3);
  translate([-12,-5,0]) cylinder(h=8, r=3);
  translate([10,5,0]) cylinder(h=8, r=3);
  translate([10,-5,0]) cylinder(h=8, r=3);
  translate([-15,0,10]) rotate([0,90,0]) cylinder(h=15, r=2, center=true);
}""",
    "bird": """union() {
  translate([0,0,0]) sphere(r=8);
  translate([-12,0,0]) rotate([0,90,0]) cylinder(h=8, r=3, center=true);
  translate([8,0,2]) sphere(r=5);
  translate([11,1,4]) sphere(r=1);
  translate([-5,8,0]) rotate([0,30,0]) cube([3,15,3], center=true);
  translate([-5,-8,0]) rotate([0,-30,0]) cube([3,15,3], center=true);
  translate([0,0,-8]) cylinder(h=8, r=2);
}""",
}

def find_shape_in_library(text):
    text_lower = text.lower()
    for shape, code in SHAPES.items():
        if shape in text_lower:
            return code
    return None


# ─── Caption → OpenSCAD heuristic conversion ────────────────────────
# Used when the image caption from BLIP doesn't match any shape in the
# SHAPES library and Ollama is unavailable (e.g. on Railway).  This
# analyses the caption keywords to produce a reasonable 3D approximation.

# Keyword → shape mapping (checked in priority order).
_CAPTION_SHAPE_MAP = [
    # People / animals / characters
    (["person", "man", "woman", "people", "human", "boy", "girl", "child"],
     "union() {\n  cylinder(h=30, r=5);\n  translate([0,0,30]) sphere(r=8);\n  translate([-6,0,38]) sphere(r=2);\n  translate([6,0,38]) sphere(r=2);\n}"),
    (["cat", "kitten"], SHAPES["cat"]),
    (["dog", "puppy"],
     "union() {\n  cube([30,15,15], center=true);\n  translate([12,0,5]) sphere(r=8);\n  translate([15,5,10]) cylinder(h=6, r1=3, r2=1);\n  translate([15,-5,10]) cylinder(h=6, r1=3, r2=1);\n  translate([-15,5,0]) cylinder(h=12, r=3);\n  translate([-15,-5,0]) cylinder(h=12, r=3);\n}"),
    # Furniture
    (["chair", "stool"], SHAPES["chair"]),
    (["table", "desk"], SHAPES["table"]),
    (["sofa", "couch"],
     "union() {\n  cube([60,25,15], center=true);\n  translate([0,12,12]) cube([60,8,20], center=true);\n  translate([-25,-12,0]) cylinder(h=10, r=3);\n  translate([25,-12,0]) cylinder(h=10, r=3);\n  translate([-25,12,0]) cylinder(h=10, r=3);\n  translate([25,12,0]) cylinder(h=10, r=3);\n}"),
    # Buildings / structures
    (["house", "home", "building", "cottage", "cabin", "hut"], SHAPES["house"]),
    (["tower", "skyscraper"],
     "union() {\n  cube([20,20,60], center=true);\n  translate([0,0,35]) cylinder(h=10, r1=12, r2=2);\n}"),
    (["castle"],
     "union() {\n  cube([40,40,30], center=true);\n  translate([-15,-15,20]) cylinder(h=15, r=5);\n  translate([15,-15,20]) cylinder(h=15, r=5);\n  translate([-15,15,20]) cylinder(h=15, r=5);\n  translate([15,15,20]) cylinder(h=15, r=5);\n}"),
    (["church"],
     "union() {\n  cube([30,50,20], center=true);\n  translate([0,0,20]) cylinder(h=25, r1=8, r2=0);\n}"),
    (["bridge"],
     "union() {\n  translate([0,0,5]) cube([60,10,4], center=true);\n  translate([-20,-8,0]) cylinder(h=10, r=5);\n  translate([20,-8,0]) cylinder(h=10, r=5);\n  translate([-20,8,0]) cylinder(h=10, r=5);\n  translate([20,8,0]) cylinder(h=10, r=5);\n}"),
    # Vehicles
    (["car", "vehicle", "automobile", "sedan"], SHAPES["car"]),
    (["truck", "lorry"],
     "union() {\n  cube([70,25,15], center=true);\n  translate([20,0,12]) cube([25,22,15], center=true);\n  translate([-25,-15,0]) cylinder(h=5, r=8);\n  translate([25,-15,0]) cylinder(h=5, r=8);\n  translate([-25,15,0]) cylinder(h=5, r=8);\n  translate([25,15,0]) cylinder(h=5, r=8);\n}"),
    (["rocket", "missile", "spaceship"], SHAPES["rocket"]),
    (["plane", "airplane", "aircraft"],
     "union() {\n  cylinder(h=40, r=4);\n  translate([0,0,20]) rotate([0,0,0]) cube([4,30,2], center=true);\n  translate([0,0,15]) cube([2,6,12], center=true);\n}"),
    (["boat", "ship"],
     "union() {\n  cylinder(h=5, r1=20, r2=15);\n  translate([0,0,5]) cube([4,30,20], center=true);\n}"),
    (["bicycle", "bike"],
     "union() {\n  cylinder(h=2, r=15);\n  translate([0,30,0]) cylinder(h=2, r=15);\n  translate([0,15,15]) cube([2,30,2], center=true);\n}"),
    # Nature
    (["tree", "oak", "pine", "forest"], SHAPES["tree"]),
    (["flower"],
     "union() {\n  cylinder(h=20, r=2);\n  translate([0,0,20]) sphere(r=8);\n  translate([6,0,22]) sphere(r=3);\n  translate([-6,0,22]) sphere(r=3);\n  translate([0,6,22]) sphere(r=3);\n  translate([0,-6,22]) sphere(r=3);\n}"),
    (["mountain"],
     "cylinder(h=40, r1=30, r2=0);"),
    (["mushroom"], SHAPES["mushroom"]),
    # Food / objects
    (["bottle", "flask"], SHAPES["bottle"]),
    (["cup", "mug", "glass"],
     "union() {\n  cylinder(h=15, r=8);\n  translate([10,0,10]) rotate([90,0,0]) cylinder(h=4, r=5);\n}"),
    (["bowl"],
     "union() {\n  cylinder(h=8, r1=15, r2=12);\n  cylinder(h=6, r1=13, r2=10);\n}"),
    (["ball", "sphere", "orb", "marble"], SHAPES["sphere"]),
    (["box", "crate", "container", "package", "cardboard"], SHAPES["box"]),
    (["phone", "smartphone", "mobile"], SHAPES["phone"]),
    (["bat", "baseball bat", "club"], SHAPES["bat"]),
    (["star"], SHAPES["star"]),
    (["heart", "love", "valentine"], SHAPES["heart"]),
    (["ring", "band", "jewelry"], SHAPES["ring"]),
    (["trophy", "cup award", "medal"], SHAPES["trophy"]),
    (["pyramid", "triangle"], SHAPES["pyramid"]),
    (["snowman"], SHAPES["snowman"]),
    # Geometric primitives (fallback patterns)
    (["cone", "funnel"], SHAPES["cone"]),
    (["cylinder", "pipe", "tube", "column", "pillar"], SHAPES["cylinder"]),
]


def _caption_to_scad(caption: str) -> str:
    """Convert an image caption (from BLIP) to OpenSCAD code using heuristics.

    This is used when Ollama is not available (e.g. on Railway) and the
    caption doesn't match the SHAPES library directly.  It scans the
    caption for keywords and returns the best-matching OpenSCAD shape.
    """
    cap_lower = caption.lower()

    # Try keyword-based matching
    for keywords, scad in _CAPTION_SHAPE_MAP:
        for kw in keywords:
            if kw in cap_lower:
                return scad

    # Shape inference from descriptive adjectives
    if any(w in cap_lower for w in ["round", "spherical", "ball", "globe", "circular"]):
        return SHAPES["sphere"]
    if any(w in cap_lower for w in ["tall", "long", "thin", "slender", "narrow"]):
        return "cylinder(h=40, r=5);"
    if any(w in cap_lower for w in ["flat", "thin", "sheet", "plate", "panel"]):
        return "cube([40,40,3], center=true);"
    if any(w in cap_lower for w in ["cube", "box", "square", "rectangular", "block"]):
        return SHAPES["box"]
    if any(w in cap_lower for w in ["cylindrical", "tube", "pipe", "rod"]):
        return SHAPES["cylinder"]

    # Final fallback — a simple cube, NOT a sphere
    return SHAPES["box"]

# Known-good shape used whenever LLM output cannot be salvaged.
FALLBACK_SCAD = "union() {\n  sphere(r=10);\n  translate([0,0,10]) cube([5,5,5], center=true);\n}"

# A line is a variable assignment if it starts with `name =` (e.g. "r = 5;").
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_]\w*\s*=")


def sanitize_scad(code: str) -> str:
    """Clean raw LLM output into renderable OpenSCAD code."""
    # 1. Strip markdown fences
    code = re.sub(r"```[a-zA-Z]*", "", code).replace("```", "").strip()

    # 2. Remove variable assignments and comments
    clean_lines = []
    for line in code.split("\n"):
        stripped = line.strip()
        if _ASSIGNMENT_RE.match(stripped):
            continue
        if stripped.startswith("//"):
            continue
        clean_lines.append(line)
    code = "\n".join(clean_lines).strip()

    # 3. Trim leading prose before the first OpenSCAD keyword
    for keyword in ["union", "difference", "intersection", "cube", "cylinder", "sphere", "translate"]:
        if keyword in code:
            code = code[code.find(keyword):]
            break

    # 4. Fix common LLM syntax mistakes
    for wrong, right in [
        ("union{}", "union(){}"),
        ("union {}", "union(){}"),
        ("difference{}", "difference(){}"),
        ("intersection{}", "intersection(){}"),
    ]:
        code = code.replace(wrong, right)

    # 5. Fallback if nothing valid remains
    if not any(k in code for k in ["cube", "sphere", "cylinder", "union"]):
        code = FALLBACK_SCAD
    return code


def ollama_generate(prompt: str, model: str = None) -> str:
    """Call Ollama via OpenAI-compatible API. Returns the text response."""
    model = model or TEXT_MODEL
    try:
        response = ollama_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ollama error ({model}): {e}")
        return ""


def ollama_vision(image_base64: str, prompt: str, model: str = None) -> str:
    """Call Ollama vision model with an image. Returns text description."""
    model = model or VISION_MODEL
    try:
        response = ollama_client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=200,
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ollama vision error ({model}): {e}")
        return ""


# ─── Local image analysis (no external API needed) ──────────────────
# Uses Pillow to extract visual features (aspect ratio, dominant colors,
# edge density, symmetry) and infer a shape. Works on Railway without
# any API key or external service.

def _local_image_analysis(image_bytes: bytes) -> str:
    """Analyze image locally using Pillow and return a description.

    Extracts:
    - Aspect ratio (tall, wide, square)
    - Dominant colors (for material/texture hints)
    - Edge density (simple vs complex shape)
    - Bounding-box fill ratio (solid vs sparse)

    Returns a descriptive string like "a tall green object" that the
    heuristic converter can map to an OpenSCAD shape.
    """
    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        w, h = img.size

        # Sample a small version for speed
        img_small = img.resize((64, 64))
        pixels = list(img_small.getdata())

        # --- Aspect ratio ---
        ratio = h / w if w > 0 else 1
        if ratio > 1.5:
            shape_hint = "tall"
        elif ratio < 0.6:
            shape_hint = "wide"
        else:
            shape_hint = "square"

        # --- Dominant color ---
        r_sum = g_sum = b_sum = 0
        for r, g, b in pixels:
            r_sum += r
            g_sum += g
            b_sum += b
        n = len(pixels)
        avg_r = r_sum / n
        avg_g = g_sum / n
        avg_b = b_sum / n

        # Color name
        if avg_r > 150 and avg_g < 100 and avg_b < 100:
            color_name = "red"
        elif avg_g > 150 and avg_r < 100:
            color_name = "green"
        elif avg_b > 150 and avg_r < 100:
            color_name = "blue"
        elif avg_r > 200 and avg_g > 200 and avg_b < 100:
            color_name = "yellow"
        elif avg_r > 100 and avg_g < 80 and avg_b < 80:
            color_name = "brown"
        elif avg_r > 200 and avg_g > 200 and avg_b > 200:
            color_name = "white"
        elif avg_r < 80 and avg_g < 80 and avg_b < 80:
            color_name = "black"
        elif avg_r > 150 and avg_g > 100 and avg_b < 100:
            color_name = "orange"
        elif avg_r > 100 and avg_g > 80 and avg_b < 80:
            color_name = "brown"
        else:
            color_name = "colored"

        # --- Edge density (complexity) ---
        # Simple: few edges → geometric shape. Many edges → complex object.
        gray = img_small.convert("L")
        gray_pixels = list(gray.getdata())
        edge_count = 0
        for y in range(64):
            for x in range(63):
                idx = y * 64 + x
                if abs(gray_pixels[idx] - gray_pixels[idx + 1]) > 30:
                    edge_count += 1
        edge_density = edge_count / (64 * 63)
        if edge_density > 0.15:
            complexity = "detailed"
        else:
            complexity = "simple"

        # --- Fill ratio (solid vs hollow/sparse) ---
        # Count non-background pixels (deviation from corners)
        corners = [pixels[0], pixels[63], pixels[64 * 63], pixels[64 * 63 - 1]]
        bg_r = sum(c[0] for c in corners) / 4
        bg_g = sum(c[1] for c in corners) / 4
        bg_b = sum(c[2] for c in corners) / 4
        non_bg = 0
        for r, g, b in pixels:
            if abs(r - bg_r) > 30 or abs(g - bg_g) > 30 or abs(b - bg_b) > 30:
                non_bg += 1
        fill_ratio = non_bg / n
        if fill_ratio > 0.7:
            solidity = "solid"
        elif fill_ratio > 0.3:
            solidity = "medium"
        else:
            solidity = "sparse"

        # --- Build description ---
        parts = [shape_hint, color_name]
        if complexity == "detailed":
            parts.append("detailed")
        if solidity == "solid":
            parts.append("solid")

        desc = "a " + " ".join(parts) + " object"
        print(f"Image analysis: {desc} (ratio={ratio:.2f}, edges={edge_density:.2f}, fill={fill_ratio:.2f})")
        return desc

    except Exception as e:
        print(f"Local image analysis error: {e}")
        return ""


def describe_image(image_bytes: bytes, image_base64: str) -> str:
    """Get a description of the image. Tries Ollama vision first (local),
    falls back to local Pillow-based image analysis (no external API needed).

    Returns a non-empty description, or empty string if both fail.
    """
    # Try Ollama first (fast if running locally with vision model)
    desc = ollama_vision(
        image_base64,
        "Describe this object in 1 sentence for 3D modeling. Focus on shape, size, key features.",
    )
    if desc and len(desc) > 5 and "simple cube" not in desc.lower():
        return desc

    # Fall back to local image analysis (Pillow — no external API needed)
    desc = _local_image_analysis(image_bytes)
    if desc and len(desc) > 3:
        return desc.strip()

    return ""


def render(scad_code, scad_path, png_path, stl_path):
    """Render OpenSCAD code to PNG preview and STL file."""
    with open(scad_path, "w") as f:
        f.write(scad_code)
    # Use xvfb-run on Linux if available, else direct openscad
    use_xvfb = os.path.exists("/usr/bin/xvfb-run")
    cmd_prefix = ["xvfb-run", "-a", OPENSCAD_BIN] if use_xvfb else [OPENSCAD_BIN]
    # Render PNG preview with fixed camera so size changes are visible.
    # --camera uses translate,rotate,distance format: the model is centered
    # at origin, viewed from distance 120, so scaling is visually obvious.
    subprocess.run(
        cmd_prefix + [
            "--imgsize=800,600",
            "--camera=0,0,0,0,0,0,120",
            "-o", png_path, scad_path,
        ],
        capture_output=True, timeout=60,
    )
    # Export STL
    subprocess.run(
        cmd_prefix + ["-o", stl_path, scad_path],
        capture_output=True, timeout=60,
    )


def find_shape(prompt: str) -> str:
    """Try shape library first, then fall back to Ollama LLM."""
    prompt_lower = prompt.lower()
    for key in SHAPES:
        if key in prompt_lower:
            return SHAPES[key]
    # Check SHAPES library (second pass with broader matching)
    library_code = find_shape_in_library(prompt)
    if library_code:
        return library_code
    # Use Ollama for unknown shapes
    code = ollama_generate(
        "Generate simple OpenSCAD code using ONLY cube(), sphere(), cylinder(), translate(), union(). "
        "NO variables. NO loops. Return ONLY code. For: " + prompt
    )
    code = sanitize_scad(code)
    return code


# ─── FastAPI App ──────────────────────────────────────────────────
app = FastAPI(title="3D Model Generator API — Ollama Edition")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PromptRequest(BaseModel):
    prompt: str


class RefineRequest(BaseModel):
    previous_scad: str
    instruction: str


@app.get("/")
async def root():
    return {
        "message": "3D Model Generator API Running!",
        "engine": "Ollama",
        "text_model": TEXT_MODEL,
        "vision_model": VISION_MODEL,
        "openscad": OPENSCAD_BIN,
    }

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/generate")
async def generate(request: PromptRequest):
    name = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scad_path = f"{base}/models/{name}.scad"
    png_path = f"{base}/outputs/{name}.png"
    stl_path = f"{base}/outputs/{name}.stl"
    scad_code = find_shape(request.prompt)
    render(scad_code, scad_path, png_path, stl_path)
    if not os.path.exists(png_path):
        return {"error": "Render failed", "scad_code": scad_code}
    with open(png_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode()
    return {"scad_code": scad_code, "image": img_base64, "status": "success"}


def parametric_refine(scad_code: str, instruction: str) -> str:
    """Refine OpenSCAD code locally without an LLM.

    Parses the instruction for keywords (bigger, smaller, taller, wider,
    rotate, move) and applies numeric transformations to the code.
    """
    instr = instruction.lower().strip()
    code = scad_code

    # Determine scale factor
    scale = 1.0
    if any(w in instr for w in ["bigger", "larger", "huge", "massive", "enormous"]):
        scale = 1.5
    elif any(w in instr for w in ["smaller", "tiny", "mini", "shrink"]):
        scale = 0.7
    elif any(w in instr for w in ["taller", "higher", "tall"]):
        # Only scale height-like values
        code = re.sub(r'(h\s*=\s*)([\d.]+)', lambda m: f'{m.group(1)}{float(m.group(2)) * 1.5:.1f}', code)
        return code
    elif any(w in instr for w in ["wider", "wider", "broader"]):
        code = re.sub(r'(r\s*=\s*)([\d.]+)', lambda m: f'{m.group(1)}{float(m.group(2)) * 1.3:.1f}', code)
        return code
    elif any(w in instr for w in ["double", "2x", "twice"]):
        scale = 2.0
    elif any(w in instr for w in ["half", "shrink"]):
        scale = 0.5

    if scale != 1.0:
        # Scale all numeric values inside function calls
        # Match patterns like r=20, h=30, r1=15, r2=0, size=40, etc.
        code = re.sub(r'(r\d?\s*=\s*)([\d.]+)', lambda m: f'{m.group(1)}{float(m.group(2)) * scale:.1f}', code)
        code = re.sub(r'(h\s*=\s*)([\d.]+)', lambda m: f'{m.group(1)}{float(m.group(2)) * scale:.1f}', code)
        code = re.sub(r'(size\s*=\s*)([\d.]+)', lambda m: f'{m.group(1)}{float(m.group(2)) * scale:.1f}', code)

        # Scale numbers inside translate([x,y,z]) and cube([w,d,h])
        def scale_array(match):
            nums = match.group(1).split(",")
            scaled = [str(round(float(n.strip()) * scale, 1)) for n in nums]
            return f"[{', '.join(scaled)}]"

        code = re.sub(r'translate\(\[([0-9.,\s\-]+)\]', lambda m: f'translate([{scale_array(m)}'.replace("[[", "[").replace("]]", "]"), code)
        code = re.sub(r'cube\(\[([0-9.,\s\-]+)\]', lambda m: f'cube([{scale_array(m)}'.replace("[[", "[").replace("]]", "]"), code)

    # Handle rotation
    if "rotate" in instr or "turn" in instr or "flip" in instr:
        axis = "[0,0,1]"
        if "x axis" in instr or "x-axis" in instr:
            axis = "[1,0,0]"
        elif "y axis" in instr or "y-axis" in instr:
            axis = "[0,1,0]"
        code = f"rotate({axis}) {{\n{code}\n}}"

    # Handle move/translate
    if any(w in instr for w in ["move", "shift", "offset"]):
        # Try to extract direction
        if "up" in instr or "above" in instr:
            code = f"translate([0,0,10]) {{\n{code}\n}}"
        elif "down" in instr or "below" in instr:
            code = f"translate([0,0,-10]) {{\n{code}\n}}"
        elif "left" in instr:
            code = f"translate([-10,0,0]) {{\n{code}\n}}"
        elif "right" in instr:
            code = f"translate([10,0,0]) {{\n{code}\n}}"
        else:
            code = f"translate([5,5,5]) {{\n{code}\n}}"

    return code


@app.post("/refine")
async def refine(request: RefineRequest):
    name = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scad_path = f"{base}/models/{name}.scad"
    png_path = f"{base}/outputs/{name}.png"
    stl_path = f"{base}/outputs/{name}.stl"

    # Try LLM-based refinement first
    system_prompt = f"""You are an OpenSCAD code modifier.
CURRENT CODE:
{request.previous_scad}

INSTRUCTION: {request.instruction}

RULES:
- Return ONLY modified OpenSCAD code
- NO explanation, NO markdown
- If bigger or larger: multiply all numbers by 1.5
- If smaller: multiply all numbers by 0.7
- If taller: increase h values by 1.5x

MODIFIED CODE:"""

    code = ollama_generate(system_prompt)
    code = sanitize_scad(code)

    # If LLM returned nothing usable, do parametric refinement locally
    if not code.strip() or code.strip() == FALLBACK_SCAD.strip():
        code = parametric_refine(request.previous_scad, request.instruction)

    if not code.strip():
        code = request.previous_scad

    render(code, scad_path, png_path, stl_path)

    if not os.path.exists(png_path):
        return {"error": "Render failed", "scad_code": code}

    with open(png_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode()

    return {"scad_code": code, "image": img_base64, "status": "success"}


@app.get("/export/{filename}")
async def export(filename: str):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stl_path = f"{base}/outputs/{filename}.stl"
    if os.path.exists(stl_path):
        return {"stl_path": stl_path, "status": "success"}
    return {"error": "File not found"}


@app.post("/route")
async def route(request: PromptRequest):
    """Router — parametric or ai_generator."""
    prompt_lower = request.prompt.lower()

    parametric_keywords = [
        'box', 'cube', 'sphere', 'cylinder', 'cone', 'chair', 'table',
        'house', 'rocket', 'snowman', 'tree', 'car', 'bottle', 'trophy',
        'mushroom', 'cat', 'mm', 'cm', 'height', 'width', 'radius',
        'geometric', 'simple', 'basic'
    ]
    ai_keywords = [
        'realistic', 'organic', 'animal', 'person', 'face', 'dragon',
        'futuristic', 'abstract', 'spaceship', 'fantasy',
        'complex', 'detailed', 'artistic', 'sculpture', 'photo'
    ]

    parametric_score = sum(1 for k in parametric_keywords if k in prompt_lower)
    ai_score = sum(1 for k in ai_keywords if k in prompt_lower)

    path = "ai_generator" if ai_score > parametric_score else "parametric"

    return {
        "prompt": request.prompt,
        "path": path,
        "parametric_score": parametric_score,
        "ai_score": ai_score,
    }


@app.post("/generate_from_image")
async def generate_from_image(file: UploadFile = File(...)):
    """Image → 3D Model using vision AI (Ollama → HuggingFace BLIP fallback)."""
    image_data = await file.read()
    image_base64 = base64.b64encode(image_data).decode()

    # Step 1: Vision AI — describe image (Ollama first, HF BLIP fallback)
    description = describe_image(image_data, image_base64)

    # If both vision services fail, use a generic description
    if not description:
        description = "a basic geometric shape"

    # Step 2: Check SHAPES library first (keyword match against description)
    scad_code = find_shape_in_library(description)

    if not scad_code:
        # Use Ollama for unknown shapes (works locally only)
        scad_code = ollama_generate(
            "Generate simple valid OpenSCAD code. STRICT RULES: "
            "1) Use ONLY these functions: cube(), sphere(), cylinder(), translate(), union(){} "
            "2) NO variables 3) NO loops 4) NO comments "
            "5) union() uses curly braces {} only 6) Maximum 10 lines "
            "7) Return ONLY the OpenSCAD code. Object: " + description
        )
    scad_code = sanitize_scad(scad_code)

    # Step 3: If Ollama not available (e.g. on Railway), generate OpenSCAD
    # from the BLIP caption using heuristics. This ensures image-to-3D
    # works on the cloud deployment without a local Ollama server.
    if not scad_code or scad_code == FALLBACK_SCAD:
        scad_code = _caption_to_scad(description)

    # Step 4: Render
    name = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scad_path = f"{base}/models/{name}.scad"
    png_path = f"{base}/outputs/{name}.png"
    stl_path = f"{base}/outputs/{name}.stl"

    render(scad_code, scad_path, png_path, stl_path)

    if not os.path.exists(png_path):
        return {
            "error": "Render failed",
            "description": description,
            "scad_code": scad_code,
        }

    with open(png_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode()

    return {
        "description": description,
        "scad_code": scad_code,
        "image": img_base64,
        "status": "success",
    }


@app.get("/download/stl")
async def download_stl():
    """Download the latest generated STL file."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = glob.glob(f"{base}/outputs/*.stl")
    if not files:
        # Also check Docker path
        files = glob.glob("/app/outputs/*.stl")
    if not files:
        raise HTTPException(status_code=404, detail="No STL file found")
    latest = max(files, key=os.path.getctime)
    from fastapi.responses import Response
    with open(latest, "rb") as f:
        stl_data = f.read()
    return Response(
        content=stl_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": 'attachment; filename="model.stl"',
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/download/glb/{name}")
async def download_glb(name: str):
    """Download a GLB file by name (from HuggingFace mesh generation)."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    glb_path = f"{base}/outputs/{name}.glb"
    if not os.path.exists(glb_path):
        # Also check Docker path
        glb_path = f"/app/outputs/{name}.glb"
    if not os.path.exists(glb_path):
        raise HTTPException(status_code=404, detail="GLB file not found")
    from fastapi.responses import Response
    with open(glb_path, "rb") as f:
        glb_data = f.read()
    return Response(
        content=glb_data,
        media_type="model/gltf-binary",
        headers={
            "Content-Disposition": f'attachment; filename="{name}.glb"',
            "Access-Control-Allow-Origin": "*",
        },
    )


# ─── Meshy API Integration ──────────────────────────────────────────
MESHY_API_KEY = os.environ.get("MESHY_API_KEY", "")
MESHY_BASE_URL = "https://api.meshy.ai/openapi"


class MeshyTextRequest(BaseModel):
    prompt: str
    mode: str = "preview"
    should_remesh: bool = True


class MeshyImageRequest(BaseModel):
    image_url: str
    should_texture: bool = True
    enable_pbr: bool = True


async def _meshy_poll(task_id: str, task_type: str, max_attempts: int = 120, interval: float = 5.0):
    """Poll a Meshy task until completion. task_type is 'text-to-3d' or 'image-to-3d'."""
    version = "v2" if task_type == "text-to-3d" else "v1"
    poll_url = f"{MESHY_BASE_URL}/{version}/{task_type}/{task_id}"
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        for _ in range(max_attempts):
            try:
                resp = await client.get(poll_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "")
                if status == "SUCCEEDED":
                    return data
                if status == "FAILED":
                    raise HTTPException(status_code=502, detail=f"Meshy task failed: {data}")
                # PENDING or IN_PROGRESS — keep polling
                await asyncio.sleep(interval)
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"Meshy poll error: {e}")
    raise HTTPException(status_code=504, detail="Meshy task timed out")


@app.post("/meshy/text-to-3d")
async def meshy_text_to_3d(request: MeshyTextRequest):
    """Create a Meshy text-to-3D task, poll until done, return model URLs."""
    if not MESHY_API_KEY:
        raise HTTPException(status_code=500, detail="MESHY_API_KEY not set")
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    payload = {
        "mode": request.mode,
        "prompt": request.prompt,
        "should_remesh": request.should_remesh,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(f"{MESHY_BASE_URL}/v2/text-to-3d", json=payload, headers=headers)
            resp.raise_for_status()
            create_data = resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Meshy create error: {e}")

    task_id = create_data.get("result")
    if not task_id:
        raise HTTPException(status_code=502, detail=f"Meshy create returned no task id: {create_data}")

    result = await _meshy_poll(task_id, "text-to-3d")
    return {"task_id": task_id, "status": "SUCCEEDED", "model_urls": result.get("model_urls", {}), "raw": result}


@app.post("/meshy/image-to-3d")
async def meshy_image_to_3d(request: MeshyImageRequest):
    """Create a Meshy image-to-3D task from an image URL, poll until done, return model URLs."""
    if not MESHY_API_KEY:
        raise HTTPException(status_code=500, detail="MESHY_API_KEY not set")
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    payload = {
        "image_url": request.image_url,
        "should_texture": request.should_texture,
        "enable_pbr": request.enable_pbr,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(f"{MESHY_BASE_URL}/v1/image-to-3d", json=payload, headers=headers)
            resp.raise_for_status()
            create_data = resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Meshy create error: {e}")

    task_id = create_data.get("result")
    if not task_id:
        raise HTTPException(status_code=502, detail=f"Meshy create returned no task id: {create_data}")

    result = await _meshy_poll(task_id, "image-to-3d")
    return {"task_id": task_id, "status": "SUCCEEDED", "model_urls": result.get("model_urls", {}), "raw": result}


@app.get("/meshy/task/{task_id}")
async def meshy_task_status(task_id: str, task_type: str = "text-to-3d"):
    """Poll a Meshy task status by task_id. Query param task_type=text-to-3d or image-to-3d."""
    if not MESHY_API_KEY:
        raise HTTPException(status_code=500, detail="MESHY_API_KEY not set")
    version = "v2" if task_type == "text-to-3d" else "v1"
    url = f"{MESHY_BASE_URL}/{version}/{task_type}/{task_id}"
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Meshy poll error: {e}")


# ─── Tripo API Integration ──────────────────────────────────────────
TRIPO_API_KEY = os.environ.get("TRIPO_API_KEY", "")
TRIPO_BASE_URL = "https://api.tripo3d.ai/v2/openapi/task"


class TripoTextRequest(BaseModel):
    prompt: str
    model_version: str = "v2.5-20250123"


class TripoImageRequest(BaseModel):
    image_url: str
    file_type: str = "jpg"


async def _tripo_poll(task_id: str, max_attempts: int = 120, interval: float = 5.0):
    """Poll a Tripo task until completion."""
    url = f"{TRIPO_BASE_URL}/{task_id}"
    headers = {"Authorization": f"Bearer {TRIPO_API_KEY}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        for _ in range(max_attempts):
            try:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                status = data.get("data", {}).get("status", "")
                if status == "success":
                    return data
                if status == "failed":
                    raise HTTPException(status_code=502, detail=f"Tripo task failed: {data}")
                # queued or running — keep polling
                await asyncio.sleep(interval)
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"Tripo poll error: {e}")
    raise HTTPException(status_code=504, detail="Tripo task timed out")


@app.post("/tripo/text-to-model")
async def tripo_text_to_model(request: TripoTextRequest):
    """Create a Tripo text-to-model task, poll until done, return model URLs."""
    if not TRIPO_API_KEY:
        raise HTTPException(status_code=500, detail="TRIPO_API_KEY not set")
    headers = {"Authorization": f"Bearer {TRIPO_API_KEY}"}
    payload = {
        "type": "text_to_model",
        "prompt": request.prompt,
        "model_version": request.model_version,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(TRIPO_BASE_URL, json=payload, headers=headers)
            resp.raise_for_status()
            create_data = resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Tripo create error: {e}")

    if create_data.get("code") != 0:
        raise HTTPException(status_code=502, detail=f"Tripo create failed: {create_data}")

    task_id = create_data.get("data", {}).get("task_id")
    if not task_id:
        raise HTTPException(status_code=502, detail=f"Tripo create returned no task id: {create_data}")

    result = await _tripo_poll(task_id)
    model_url = result.get("data", {}).get("output", {}).get("model", "")
    return {"task_id": task_id, "status": "success", "model_url": model_url, "raw": result}


@app.post("/tripo/image-to-model")
async def tripo_image_to_model(request: TripoImageRequest):
    """Create a Tripo image-to-model task from an image URL, poll until done, return model URLs."""
    if not TRIPO_API_KEY:
        raise HTTPException(status_code=500, detail="TRIPO_API_KEY not set")
    headers = {"Authorization": f"Bearer {TRIPO_API_KEY}"}
    payload = {
        "type": "image_to_model",
        "file": {"type": request.file_type, "url": request.image_url},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(TRIPO_BASE_URL, json=payload, headers=headers)
            resp.raise_for_status()
            create_data = resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Tripo create error: {e}")

    if create_data.get("code") != 0:
        raise HTTPException(status_code=502, detail=f"Tripo create failed: {create_data}")

    task_id = create_data.get("data", {}).get("task_id")
    if not task_id:
        raise HTTPException(status_code=502, detail=f"Tripo create returned no task id: {create_data}")

    result = await _tripo_poll(task_id)
    model_url = result.get("data", {}).get("output", {}).get("model", "")
    return {"task_id": task_id, "status": "success", "model_url": model_url, "raw": result}


@app.get("/tripo/task/{task_id}")
async def tripo_task_status(task_id: str):
    """Poll a Tripo task status by task_id."""
    if not TRIPO_API_KEY:
        raise HTTPException(status_code=500, detail="TRIPO_API_KEY not set")
    url = f"{TRIPO_BASE_URL}/{task_id}"
    headers = {"Authorization": f"Bearer {TRIPO_API_KEY}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Tripo poll error: {e}")


# ─── HuggingFace Spaces Integration ─────────────────────────────────
# Calls free HuggingFace Spaces via gradio_client for 3D model generation.
# HF_TOKEN is defined at the top of this file (used by both vision + spaces).

# Space URLs
HF_TRIPOSR_URL = "https://stabilityai-triposr.hf.space"
HF_STABLE_FAST_3D_URL = "https://stabilityai-stable-fast-3d.hf.space"
HF_HUNYUAN3D_URL = "https://tencent-hunyuan3d-2.hf.space"


def _hf_headers():
    """Build optional auth headers for HF Spaces."""
    if HF_TOKEN:
        return {"Authorization": f"Bearer {HF_TOKEN}"}
    return {}


def _hf_client(space_url: str):
    """Create a fresh gradio_client.Client for a Space. Don't cache — Spaces restart."""
    from gradio_client import Client
    kwargs = {}
    if HF_TOKEN:
        kwargs["hf_token"] = HF_TOKEN
    return Client(space_url, **kwargs)


def _save_upload_to_temp(file: UploadFile) -> str:
    """Save an UploadFile to a temp path and return the path for gradio_client.handle_file()."""
    import tempfile
    suffix = os.path.splitext(file.filename or "image.png")[1] or ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(file.file.read())
    tmp.close()
    return tmp.name


@app.post("/hf/triposr")
async def hf_triposr(image: UploadFile = File(...)):
    """Image → 3D via TripoSR HuggingFace Space.

    Calls /preprocess (remove background) then /generate (3D reconstruction).
    Returns OBJ + GLB model URLs.
    """
    from gradio_client import Client, handle_file

    tmp_path = _save_upload_to_temp(image)

    def _run():
        client = _hf_client(HF_TRIPOSR_URL)
        # Step 1: preprocess — remove background
        result = client.predict(
            handle_file(tmp_path),   # image
            True,                      # remove_background
            0.5,                       # foreground_ratio
            api_name="/preprocess",
        )
        # result is the processed image (filepath on the Space's server)
        processed_image = result if isinstance(result, str) else result[0]

        # Step 2: generate 3D model
        gen_result = client.predict(
            processed_image,           # processed image
            32,                         # resolution
            api_name="/generate",
        )
        return gen_result

    try:
        result = await asyncio.to_thread(_run)
    except Exception as e:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return {"error": "Space unavailable", "space": "triposr", "detail": str(e)}

    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    # Parse result — TripoSR returns (obj_path, glb_path) or similar structure
    obj_url, glb_url = None, None
    if isinstance(result, (list, tuple)):
        for item in result:
            if isinstance(item, str):
                if item.endswith(".obj"):
                    obj_url = item
                elif item.endswith(".glb"):
                    glb_url = item
            elif isinstance(item, (list, tuple)):
                for sub in item:
                    if isinstance(sub, str):
                        if sub.endswith(".obj"):
                            obj_url = sub
                        elif sub.endswith(".glb"):
                            glb_url = sub
    elif isinstance(result, str):
        if result.endswith(".obj"):
            obj_url = result
        elif result.endswith(".glb"):
            glb_url = result

    return {
        "status": "success",
        "space": "triposr",
        "obj_url": obj_url,
        "glb_url": glb_url,
        "raw": str(result),
    }


@app.post("/hf/stable-fast-3d")
async def hf_stable_fast_3d(image: UploadFile = File(...)):
    """Image → 3D via Stable Fast 3D HuggingFace Space.

    Returns GLB model URL.
    """
    from gradio_client import Client, handle_file

    tmp_path = _save_upload_to_temp(image)

    def _run():
        client = _hf_client(HF_STABLE_FAST_3D_URL)
        result = client.predict(
            handle_file(tmp_path),     # input_image
            0.85,                        # foreground_ratio
            "None",                      # remesh_option
            -1,                          # vertex_count
            1024,                        # texture_size
            api_name="/run_button",
        )
        return result

    try:
        result = await asyncio.to_thread(_run)
    except Exception as e:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return {"error": "Space unavailable", "space": "stable_fast_3d", "detail": str(e)}

    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    # Parse result — Stable Fast 3D returns GLB path
    glb_url = None
    if isinstance(result, str):
        glb_url = result
    elif isinstance(result, (list, tuple)):
        for item in result:
            if isinstance(item, str) and item.endswith(".glb"):
                glb_url = item
                break
            if isinstance(item, (list, tuple)):
                for sub in item:
                    if isinstance(sub, str) and sub.endswith(".glb"):
                        glb_url = sub
                        break

    return {
        "status": "success",
        "space": "stable_fast_3d",
        "glb_url": glb_url,
        "raw": str(result),
    }


class Hunyuan3DTextRequest(BaseModel):
    caption: str


@app.post("/hf/hunyuan3d")
async def hf_hunyuan3d(
    image: UploadFile = File(None),
    caption: str = None,
):
    """Text OR Image → 3D via Hunyuan3D-2 HuggingFace Space.

    Accepts either:
      - Image upload (FormData: image file)
      - Text prompt (FormData: caption field, or JSON body via Hunyuan3DTextRequest)

    Returns GLB/OBJ model file + mesh stats.
    """
    from gradio_client import Client, handle_file

    # Determine if we have text or image input
    has_image = image is not None and image.filename is not None
    has_text = caption is not None and caption.strip() != ""

    if not has_image and not has_text:
        return {"error": "Provide either an image upload or a text caption", "space": "hunyuan3d"}

    tmp_path = None
    if has_image:
        tmp_path = _save_upload_to_temp(image)

    def _run():
        client = _hf_client(HF_HUNYUAN3D_URL)
        image_arg = handle_file(tmp_path) if tmp_path else None
        result = client.predict(
            caption or "",               # caption (text prompt)
            image_arg,                    # image (uploaded image or None)
            None, None, None, None,       # mv_image_front/back/left/right
            30,                           # steps
            5.0,                          # guidance_scale
            1234,                         # seed
            256,                          # octree_resolution
            True,                         # check_box_rembg
            8000,                         # num_chunks
            True,                         # randomize_seed
            api_name="/shape_generation",
        )
        return result

    try:
        result = await asyncio.to_thread(_run)
    except Exception as e:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return {"error": "Space unavailable", "space": "hunyuan3d", "detail": str(e)}

    if tmp_path:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # Parse result — Hunyuan3D-2 returns (file_dict, html_str, stats_dict, seed)
    # file_dict is {'value': '/path/to/white_mesh.glb', '__type__': 'update'}
    glb_path = None
    obj_path = None
    mesh_stats = None
    if isinstance(result, (list, tuple)):
        for item in result:
            if isinstance(item, dict) and "value" in item:
                val = item["value"]
                if isinstance(val, str) and val.endswith(".glb"):
                    glb_path = val
                elif isinstance(val, str) and val.endswith(".obj"):
                    obj_path = val
            elif isinstance(item, str):
                if item.endswith(".glb"):
                    glb_path = item
                elif item.endswith(".obj"):
                    obj_path = item
            elif isinstance(item, dict):
                mesh_stats = item

    # Copy the GLB file to our outputs directory so we can serve it
    glb_url = None
    if glb_path and os.path.exists(glb_path):
        name = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dest = f"{base}/outputs/{name}.glb"
        import shutil as _shutil
        _shutil.copy(glb_path, dest)
        glb_url = f"/download/glb/{name}"

    return {
        "status": "success",
        "space": "hunyuan3d",
        "glb_url": glb_url,
        "obj_url": None,
        "mesh_stats": mesh_stats,
        "raw": str(result)[:500],
    }


@app.get("/hf/status")
async def hf_status():
    """Check which HuggingFace Spaces are online."""
    spaces = {
        "triposr": HF_TRIPOSR_URL,
        "stable_fast_3d": HF_STABLE_FAST_3D_URL,
        "hunyuan3d": HF_HUNYUAN3D_URL,
    }
    status = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in spaces.items():
            try:
                resp = await client.get(url, headers=_hf_headers())
                if resp.status_code < 500:
                    status[name] = "online"
                else:
                    status[name] = "offline"
            except Exception:
                status[name] = "offline"
    return status


# ─── Parametric Modeling ──────────────────────────────────────────
try:
    from scripts.parametric import TEMPLATES as PARAMETRIC_TEMPLATES, generate_parametric
except ModuleNotFoundError:
    from parametric import TEMPLATES as PARAMETRIC_TEMPLATES, generate_parametric


@app.get("/parametric/templates")
async def list_parametric_templates():
    """List all available parametric templates."""
    result = []
    for tid, tmpl in PARAMETRIC_TEMPLATES.items():
        result.append({
            "id": tid,
            "name": tmpl["name"],
            "category": tmpl["category"],
            "description": tmpl["description"],
            "parameters": tmpl["parameters"],
        })
    return {"templates": result}


@app.post("/parametric/generate")
async def generate_parametric_model(request: dict):
    """Generate a 3D model from a parametric template.

    Body: {"template_id": "adjustable_box", "parameters": {"width": 60, "height": 40, ...}}
    """
    template_id = request.get("template_id")
    params = request.get("parameters", {})

    if not template_id or template_id not in PARAMETRIC_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Unknown template: {template_id}")

    result = generate_parametric(template_id, params)

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    return {
        "status": "success",
        "template_id": template_id,
        "template_name": PARAMETRIC_TEMPLATES[template_id]["name"],
        "scad_code": result.get("scad_code", ""),
        "image": result.get("image", ""),
        "stl_path": result.get("stl_path", ""),
    }


@app.get("/parametric/categories")
async def list_categories():
    """List all template categories."""
    cats = {}
    for tid, tmpl in PARAMETRIC_TEMPLATES.items():
        cat = tmpl["category"]
        if cat not in cats:
            cats[cat] = []
        cats[cat].append({"id": tid, "name": tmpl["name"]})
    return {"categories": cats}


# ─── AI Design Studio ──────────────────────────────────────────────
# Token-optimized AI agent for interactive 3D design.
# Constitution Article 4: Prefer local models over paid APIs.
# Routing: parametric (0 tokens) → mistral (few tokens) → glm4 (more tokens).

import uuid
import json as _json

# Sliding-window conversation history (per-session, last 3 messages only).
# Keyed by a client-provided session_id (falls back to "default").
_studio_conversations: dict[str, list[dict]] = {}


def _studio_history(session_id: str, window: int = 3) -> list[dict]:
    """Return the last `window` messages for a session (sliding window)."""
    msgs = _studio_conversations.setdefault(session_id, [])
    return msgs[-window:] if len(msgs) > window else msgs[:]


def _studio_append(session_id: str, role: str, content: str, window: int = 6):
    """Append a message and trim to keep only the last `window` entries."""
    msgs = _studio_conversations.setdefault(session_id, [])
    msgs.append({"role": role, "content": content})
    if len(msgs) > window:
        _studio_conversations[session_id] = msgs[-window:]


# ─── Scene → OpenSCAD conversion ───────────────────────────────────

def object_to_scad(obj: dict, indent: int = 0) -> str:
    """Convert a single scene object to OpenSCAD code.

    Supports: cube, sphere, cylinder, cone, union, difference.
    Handles nested children for union/difference.
    """
    t = obj.get("type", "cube")
    p = obj.get("params", {})
    x = p.get("x", 0)
    y = p.get("y", 0)
    z = p.get("z", 0)
    rot = p.get("rotation", [0, 0, 0])
    pad = "  " * indent
    prefix = f"{pad}translate([{x},{y},{z}]) rotate([{rot[0]},{rot[1]},{rot[2]}]) "

    if t == "cube":
        size = p.get("size", 10)
        # Allow per-axis dimensions: {"w": .., "d": .., "h": ..}
        w = p.get("w", size)
        d = p.get("d", size)
        h = p.get("h", size)
        return prefix + f"cube([{w},{d},{h}], center=true);"
    elif t == "sphere":
        return prefix + f"sphere(r={p.get('radius', 10)});"
    elif t == "cylinder":
        return prefix + f"cylinder(h={p.get('height', 20)}, r={p.get('radius', 5)});"
    elif t == "cone":
        return prefix + f"cylinder(h={p.get('height', 20)}, r1={p.get('radius', 10)}, r2=0);"
    elif t == "union":
        lines = [f"{pad}union() {{"]
        for child in obj.get("children", []):
            lines.append(object_to_scad(child, indent + 1))
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    elif t == "difference":
        lines = [f"{pad}difference() {{"]
        for child in obj.get("children", []):
            lines.append(object_to_scad(child, indent + 1))
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    else:
        # Unknown type — fallback to cube
        return prefix + f"cube([{p.get('size', 10)},{p.get('size', 10)},{p.get('size', 10)}], center=true);"


def scene_to_scad(scene: dict) -> str:
    """Convert a full scene (list of objects) to OpenSCAD code."""
    objects = scene.get("objects", [])
    if not objects:
        return "// empty scene"
    code = ""
    for obj in objects:
        code += object_to_scad(obj) + "\n"
    return code


# ─── Parametric detection (0 tokens) ──────────────────────────────

# Pre-compiled regex patterns for common shape commands.
_RE_ADD_CUBE = re.compile(
    r"add\s+(?:a\s+)?cube\b.*?(\d+)\s*(?:mm)?\s*(?:x\s*(\d+)\s*(?:mm)?\s*)?(?:x\s*(\d+)\s*(?:mm)?)?",
    re.IGNORECASE,
)
_RE_ADD_SPHERE = re.compile(
    r"add\s+(?:a\s+)?sphere\b.*?(\d+)\s*(?:mm)?", re.IGNORECASE,
)
_RE_ADD_CYLINDER = re.compile(
    r"add\s+(?:a\s+)?cylinder\b.*?(\d+)\s*(?:mm)?\s*(?:radius|r)\s*(\d+)\s*(?:mm)?.*?(\d+)\s*(?:mm)?\s*(?:tall|height|h)\b",
    re.IGNORECASE,
)
_RE_ADD_CYLINDER_ALT = re.compile(
    r"add\s+(?:a\s+)?cylinder\b.*?(?:radius|r)\s*(\d+)\s*(?:mm)?.*?(?:height|h|tall)\s*(\d+)\s*(?:mm)?",
    re.IGNORECASE,
)
_RE_DELETE = re.compile(
    r"(?:delete|remove)\s+(?:object\s+)?([\w-]+)", re.IGNORECASE,
)
_RE_MOVE = re.compile(
    r"move\s+(?:object\s+)?([\w-]+)\s+(?:to\s+)?x\s*[:=]?\s*(-?\d+)\s+y\s*[:=]?\s*(-?\d+)\s+z\s*[:=]?\s*(-?\d+)",
    re.IGNORECASE,
)
_RE_ROTATE = re.compile(
    r"rotate\s+(?:object\s+)?([\w-]+)\s+(?:by\s+)?(-?\d+)\s*(-?\d+)\s*(-?\d+)",
    re.IGNORECASE,
)
_RE_SCALE = re.compile(
    r"scale\s+(?:object\s+)?([\w-]+)\s+(?:by\s+)?([\d.]+)", re.IGNORECASE,
)
_RE_EXPORT_STL = re.compile(r"export\s+(?:to\s+)?stl", re.IGNORECASE)
_RE_EXPORT_OBJ = re.compile(r"export\s+(?:to\s+)?obj", re.IGNORECASE)


def _new_id() -> str:
    """Generate a unique object ID."""
    return f"obj_{uuid.uuid4().hex[:8]}"


def parametric_detect(message: str, scene: dict) -> dict | None:
    """Try to handle a simple command WITHOUT calling the LLM.

    Returns a dict with reply + actions if matched, else None.
    Token cost: 0.
    """
    msg = message.strip()

    # --- Export to STL ---
    if _RE_EXPORT_STL.search(msg):
        return {
            "reply": "Exporting scene to STL.",
            "actions": [{"type": "export", "format": "stl"}],
            "model_used": "parametric",
            "tokens_used": 0,
        }
    if _RE_EXPORT_OBJ.search(msg):
        return {
            "reply": "Exporting scene to OBJ.",
            "actions": [{"type": "export", "format": "obj"}],
            "model_used": "parametric",
            "tokens_used": 0,
        }

    # --- Add cube ---
    m = _RE_ADD_CUBE.search(msg)
    if m:
        s1 = int(m.group(1))
        s2 = int(m.group(2)) if m.group(2) else s1
        s3 = int(m.group(3)) if m.group(3) else s1
        obj_id = _new_id()
        obj = {
            "id": obj_id,
            "type": "cube",
            "params": {"size": s1, "w": s1, "d": s2, "h": s3, "x": 0, "y": 0, "z": 0, "rotation": [0, 0, 0]},
        }
        return {
            "reply": f"Added a cube {s1}×{s2}×{s3}mm.",
            "actions": [{"type": "add", "object": obj}],
            "model_used": "parametric",
            "tokens_used": 0,
        }

    # --- Add sphere ---
    m = _RE_ADD_SPHERE.search(msg)
    if m:
        r = int(m.group(1))
        obj_id = _new_id()
        obj = {
            "id": obj_id,
            "type": "sphere",
            "params": {"radius": r, "x": 0, "y": 0, "z": 0, "rotation": [0, 0, 0]},
        }
        return {
            "reply": f"Added a sphere with radius {r}mm.",
            "actions": [{"type": "add", "object": obj}],
            "model_used": "parametric",
            "tokens_used": 0,
        }

    # --- Add cylinder (two patterns) ---
    m = _RE_ADD_CYLINDER.search(msg)
    if m:
        h = int(m.group(1))
        r = int(m.group(2))
        h2 = int(m.group(3))
        obj_id = _new_id()
        obj = {
            "id": obj_id,
            "type": "cylinder",
            "params": {"radius": r, "height": h2, "x": 0, "y": 0, "z": 0, "rotation": [0, 0, 0]},
        }
        return {
            "reply": f"Added a cylinder with radius {r}mm and height {h2}mm.",
            "actions": [{"type": "add", "object": obj}],
            "model_used": "parametric",
            "tokens_used": 0,
        }

    m = _RE_ADD_CYLINDER_ALT.search(msg)
    if m:
        r = int(m.group(1))
        h = int(m.group(2))
        obj_id = _new_id()
        obj = {
            "id": obj_id,
            "type": "cylinder",
            "params": {"radius": r, "height": h, "x": 0, "y": 0, "z": 0, "rotation": [0, 0, 0]},
        }
        return {
            "reply": f"Added a cylinder with radius {r}mm and height {h}mm.",
            "actions": [{"type": "add", "object": obj}],
            "model_used": "parametric",
            "tokens_used": 0,
        }

    # --- Delete object ---
    m = _RE_DELETE.search(msg)
    if m:
        obj_id = m.group(1)
        return {
            "reply": f"Deleted object {obj_id}.",
            "actions": [{"type": "delete", "id": obj_id}],
            "model_used": "parametric",
            "tokens_used": 0,
        }

    # --- Move object ---
    m = _RE_MOVE.search(msg)
    if m:
        obj_id = m.group(1)
        x, y, z = int(m.group(2)), int(m.group(3)), int(m.group(4))
        return {
            "reply": f"Moved object {obj_id} to ({x}, {y}, {z}).",
            "actions": [{"type": "move", "id": obj_id, "params": {"x": x, "y": y, "z": z}}],
            "model_used": "parametric",
            "tokens_used": 0,
        }

    # --- Rotate object ---
    m = _RE_ROTATE.search(msg)
    if m:
        obj_id = m.group(1)
        rx, ry, rz = float(m.group(2)), float(m.group(3)), float(m.group(4))
        return {
            "reply": f"Rotated object {obj_id} by ({rx}, {ry}, {rz}).",
            "actions": [{"type": "rotate", "id": obj_id, "params": {"rotation": [rx, ry, rz]}}],
            "model_used": "parametric",
            "tokens_used": 0,
        }

    # --- Scale object ---
    m = _RE_SCALE.search(msg)
    if m:
        obj_id = m.group(1)
        factor = float(m.group(2))
        return {
            "reply": f"Scaled object {obj_id} by {factor}x.",
            "actions": [{"type": "scale", "id": obj_id, "factor": factor}],
            "model_used": "parametric",
            "tokens_used": 0,
        }

    return None  # No parametric match — needs LLM


# ─── Minimal LLM call (mistral, few tokens) ───────────────────────

def _llm_minimal(message: str, scene: dict) -> dict:
    """Use mistral for slight interpretation of geometric commands.

    Token cost: low (max_tokens=100).
    """
    # Build a compact scene summary (object list only, no code)
    obj_list = []
    for obj in scene.get("objects", []):
        obj_list.append({
            "id": obj.get("id", ""),
            "type": obj.get("type", ""),
            "params": obj.get("params", {}),
        })
    scene_json = _json.dumps({"objects": obj_list})

    system_prompt = (
        "You are a 3D design assistant. Convert the user's message into a JSON action.\n"
        "Return ONLY a JSON object, no explanation.\n"
        "Actions: {\"type\":\"add\",\"object\":{\"type\":\"cube|sphere|cylinder|cone\","
        "\"params\":{\"size\":N,\"radius\":N,\"height\":N,\"x\":N,\"y\":N,\"z\":N,"
        "\"rotation\":[0,0,0]}}}\n"
        "Other actions: {\"type\":\"delete|move|rotate|scale\",\"id\":\"obj_id\",...}\n"
        f"Current scene: {scene_json}\n"
        f"User message: {message}\n"
        "JSON:"
    )

    try:
        response = ollama_client.chat.completions.create(
            model="mistral",
            messages=[{"role": "user", "content": system_prompt}],
            max_tokens=100,
            temperature=0.0,
        )
        content = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens if response.usage else 0
        # Parse the JSON action
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"```[a-zA-Z]*", "", content).replace("```", "").strip()
        action = _json.loads(content)
        return {
            "reply": f"Processed: {message}",
            "actions": [action],
            "model_used": "mistral",
            "tokens_used": tokens_used,
        }
    except Exception as e:
        print(f"Studio minimal LLM error: {e}")
        return {
            "reply": f"Sorry, I couldn't process that. ({e})",
            "actions": [],
            "model_used": "mistral",
            "tokens_used": 0,
        }


# ─── Full LLM call (glm4, more tokens) ─────────────────────────────

def _llm_full(message: str, scene: dict, history: list[dict]) -> dict:
    """Use glm4 for complex/creative design requests.

    Token cost: higher (max_tokens=500). Includes scene context (object list only).
    """
    obj_list = []
    for obj in scene.get("objects", []):
        obj_list.append({
            "id": obj.get("id", ""),
            "type": obj.get("type", ""),
            "params": obj.get("params", {}),
        })
    scene_json = _json.dumps({"objects": obj_list})

    system_prompt = (
        "You are a 3D design assistant. Convert the user's request into scene actions.\n"
        "Return ONLY a JSON array of action objects. No explanation, no markdown.\n"
        "Each action: {\"type\":\"add\",\"object\":{\"type\":\"cube|sphere|cylinder|cone|union|difference\","
        "\"params\":{\"size\":N,\"radius\":N,\"height\":N,\"x\":N,\"y\":N,\"z\":N,"
        "\"rotation\":[0,0,0]},\"children\":[...]}}\n"
        "Other actions: {\"type\":\"delete|move|rotate|scale\",\"id\":\"obj_id\",...}\n"
        f"Current scene objects: {scene_json}\n"
    )

    messages = [{"role": "system", "content": system_prompt}]
    # Sliding window: add last 3 conversation messages
    for msg in history:
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": message + "\nJSON actions:"})

    try:
        response = ollama_client.chat.completions.create(
            model=TEXT_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.1,
        )
        content = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens if response.usage else 0
        # Parse JSON actions
        if content.startswith("```"):
            content = re.sub(r"```[a-zA-Z]*", "", content).replace("```", "").strip()
        actions = _json.loads(content)
        if isinstance(actions, dict):
            actions = [actions]
        return {
            "reply": f"Processed complex request: {message}",
            "actions": actions,
            "model_used": TEXT_MODEL,
            "tokens_used": tokens_used,
        }
    except Exception as e:
        print(f"Studio full LLM error: {e}")
        return {
            "reply": f"Sorry, I couldn't process that. ({e})",
            "actions": [],
            "model_used": TEXT_MODEL,
            "tokens_used": 0,
        }


# ─── Smart routing logic ───────────────────────────────────────────

# Keywords that indicate a complex/creative request needing full LLM.
_COMPLEX_KEYWORDS = [
    "design", "create a", "build a", "mechanism", "assembly",
    "stand", "holder", "mount", "bracket", "case", "enclosure",
    "gear", "phone stand", "lamp", "articulated", "hinge",
    "complex", "detailed", "functional", "mechanical",
]


_GEOMETRY_RE = re.compile(
    r"(?:bigger|smaller|larger|shrink|double|halve|wider|taller|shorter|narrower|thicker|thinner)",
    re.IGNORECASE,
)


def _route_message(message: str) -> str:
    """Decide which route to use: 'parametric', 'minimal', or 'full'.

    - parametric: simple add/delete/move/scale/export commands (regex)
    - minimal: slight geometric interpretation (e.g. "make the box bigger")
    - full: complex/creative design requests
    """
    msg_lower = message.lower()
    # If any complex keyword is present → full LLM
    for kw in _COMPLEX_KEYWORDS:
        if kw in msg_lower:
            return "full"
    # If it looks like a simple geometric instruction → minimal LLM
    # (e.g. "make it bigger", "shrink the cylinder", "double the size")
    if _GEOMETRY_RE.search(msg_lower):
        return "minimal"
    return "full"


# ─── Pydantic models ───────────────────────────────────────────────

class StudioChatRequest(BaseModel):
    message: str
    scene: dict = {"objects": []}
    session_id: str = "default"
    history: list[dict] | None = None  # Optional override of conversation history


class StudioExportRequest(BaseModel):
    scene: dict
    format: str = "stl"


class StudioPreviewRequest(BaseModel):
    scene: dict


# ─── Endpoints ─────────────────────────────────────────────────────

@app.post("/studio/chat")
async def studio_chat(request: StudioChatRequest):
    """AI Design Studio chat — token-optimized AI agent.

    Smart routing:
    1. Parametric detection (0 tokens) — regex pattern matching
    2. Minimal LLM call (mistral, ~100 tokens) — geometric interpretation
    3. Full LLM call (glm4, ~500 tokens) — complex/creative requests
    """
    message = request.message
    scene = request.scene if request.scene else {"objects": []}
    session_id = request.session_id or "default"

    # Get conversation history (sliding window of last 3)
    history = request.history if request.history else _studio_history(session_id)

    # Step 1: Try parametric detection (0 tokens)
    result = parametric_detect(message, scene)
    if result is None:
        # Step 2: Route to minimal or full LLM
        route = _route_message(message)
        if route == "minimal":
            result = _llm_minimal(message, scene)
        else:
            result = _llm_full(message, scene, history)

    # Store in conversation history (sliding window)
    _studio_append(session_id, "user", message)
    _studio_append(session_id, "assistant", result.get("reply", ""))

    return result


@app.post("/studio/export")
async def studio_export(request: StudioExportRequest):
    """Export a scene to STL or OBJ via OpenSCAD.

    Converts scene objects → OpenSCAD code → renders to file.
    Uses asyncio.to_thread because OpenSCAD subprocess is synchronous.
    """
    scene = request.scene if request.scene else {"objects": []}
    fmt = request.format.lower()
    if fmt not in ("stl", "obj"):
        raise HTTPException(status_code=400, detail="format must be 'stl' or 'obj'")

    scad_code = scene_to_scad(scene)
    name = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scad_path = f"{base}/models/studio_{name}.scad"
    out_path = f"{base}/outputs/studio_{name}.{fmt}"

    # Write scad file
    os.makedirs(os.path.dirname(scad_path), exist_ok=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(scad_path, "w") as f:
        f.write(scad_code)

    # Render via OpenSCAD in a background thread (sync subprocess)
    def _render():
        use_xvfb = os.path.exists("/usr/bin/xvfb-run")
        cmd_prefix = ["xvfb-run", "-a", OPENSCAD_BIN] if use_xvfb else [OPENSCAD_BIN]
        subprocess.run(
            cmd_prefix + ["-o", out_path, scad_path],
            capture_output=True, timeout=60,
        )

    await asyncio.to_thread(_render)

    if not os.path.exists(out_path):
        raise HTTPException(status_code=500, detail="Export failed — OpenSCAD did not produce output")

    return {
        "stl_path": out_path,
        "scad_code": scad_code,
        "format": fmt,
    }


@app.post("/studio/preview")
async def studio_preview(request: StudioPreviewRequest):
    """Generate a PNG preview image of a scene.

    Converts scene objects → OpenSCAD code → renders PNG.
    Returns base64-encoded image + scad code.
    """
    scene = request.scene if request.scene else {"objects": []}
    scad_code = scene_to_scad(scene)
    name = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scad_path = f"{base}/models/studio_{name}.scad"
    png_path = f"{base}/outputs/studio_{name}.png"

    os.makedirs(os.path.dirname(scad_path), exist_ok=True)
    os.makedirs(os.path.dirname(png_path), exist_ok=True)
    with open(scad_path, "w") as f:
        f.write(scad_code)

    # Render PNG via OpenSCAD in a background thread
    def _render_png():
        use_xvfb = os.path.exists("/usr/bin/xvfb-run")
        cmd_prefix = ["xvfb-run", "-a", OPENSCAD_BIN] if use_xvfb else [OPENSCAD_BIN]
        subprocess.run(
            cmd_prefix + ["--imgsize=800,600", "--camera=0,0,0,0,0,0,120", "-o", png_path, scad_path],
            capture_output=True, timeout=60,
        )

    await asyncio.to_thread(_render_png)

    if not os.path.exists(png_path):
        raise HTTPException(status_code=500, detail="Preview render failed")

    # Read the PNG and encode to base64
    def _read_image():
        with open(png_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    img_base64 = await asyncio.to_thread(_read_image)

    return {
        "image": img_base64,
        "scad_code": scad_code,
    }


@app.get("/studio/templates")
async def studio_templates():
    """Get pre-made scene templates (starter scenes).

    Returns a dict of template_name → scene object.
    """
    templates = {
        "empty": {
            "name": "Empty Scene",
            "description": "A blank canvas to start designing from scratch.",
            "scene": {"objects": []},
        },
        "gear_assembly": {
            "name": "Gear Assembly",
            "description": "Three interlocking gears for mechanical demos.",
            "scene": {
                "objects": [
                    {
                        "id": "gear1",
                        "type": "cylinder",
                        "params": {"radius": 15, "height": 5, "x": 0, "y": 0, "z": 0, "rotation": [0, 0, 0]},
                    },
                    {
                        "id": "gear2",
                        "type": "cylinder",
                        "params": {"radius": 12, "height": 5, "x": 27, "y": 0, "z": 0, "rotation": [0, 0, 18]},
                    },
                    {
                        "id": "gear3",
                        "type": "cylinder",
                        "params": {"radius": 10, "height": 5, "x": 0, "y": 25, "z": 0, "rotation": [0, 0, 12]},
                    },
                ]
            },
        },
        "box_with_holes": {
            "name": "Box with Patterned Holes",
            "description": "A box with cylindrical holes punched through it.",
            "scene": {
                "objects": [
                    {
                        "id": "holey_box",
                        "type": "difference",
                        "params": {"x": 0, "y": 0, "z": 0, "rotation": [0, 0, 0]},
                        "children": [
                            {
                                "id": "box_body",
                                "type": "cube",
                                "params": {"size": 40, "w": 40, "d": 40, "h": 20, "x": 0, "y": 0, "z": 0, "rotation": [0, 0, 0]},
                            },
                            {
                                "id": "hole1",
                                "type": "cylinder",
                                "params": {"radius": 3, "height": 25, "x": -10, "y": -10, "z": 0, "rotation": [0, 0, 0]},
                            },
                            {
                                "id": "hole2",
                                "type": "cylinder",
                                "params": {"radius": 3, "height": 25, "x": 10, "y": -10, "z": 0, "rotation": [0, 0, 0]},
                            },
                            {
                                "id": "hole3",
                                "type": "cylinder",
                                "params": {"radius": 3, "height": 25, "x": -10, "y": 10, "z": 0, "rotation": [0, 0, 0]},
                            },
                            {
                                "id": "hole4",
                                "type": "cylinder",
                                "params": {"radius": 3, "height": 25, "x": 10, "y": 10, "z": 0, "rotation": [0, 0, 0]},
                            },
                        ],
                    }
                ]
            },
        },
        "phone_stand": {
            "name": "Phone Stand",
            "description": "A complete phone stand design holding a phone at 15 degrees.",
            "scene": {
                "objects": [
                    {
                        "id": "base",
                        "type": "cube",
                        "params": {"size": 60, "w": 60, "d": 40, "h": 5, "x": 0, "y": 0, "z": 0, "rotation": [0, 0, 0]},
                    },
                    {
                        "id": "back_support",
                        "type": "cube",
                        "params": {"size": 50, "w": 50, "d": 5, "h": 40, "x": 0, "y": -15, "z": 20, "rotation": [15, 0, 0]},
                    },
                    {
                        "id": "front_lip",
                        "type": "cube",
                        "params": {"size": 50, "w": 50, "d": 5, "h": 8, "x": 0, "y": 15, "z": 4, "rotation": [0, 0, 0]},
                    },
                    {
                        "id": "phone_placeholder",
                        "type": "cube",
                        "params": {"size": 8, "w": 8, "d": 16, "h": 1, "x": 0, "y": 0, "z": 25, "rotation": [15, 0, 0]},
                    },
                ]
            },
        },
    }
    return {"templates": templates}