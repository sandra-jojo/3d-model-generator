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
}

def find_shape_in_library(text):
    text_lower = text.lower()
    for shape, code in SHAPES.items():
        if shape in text_lower:
            return code
    return None

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
        return "a simple cube"


def render(scad_code, scad_path, png_path, stl_path):
    """Render OpenSCAD code to PNG preview and STL file."""
    with open(scad_path, "w") as f:
        f.write(scad_code)
    # Use xvfb-run on Linux if available, else direct openscad
    use_xvfb = os.path.exists("/usr/bin/xvfb-run")
    cmd_prefix = ["xvfb-run", "-a", OPENSCAD_BIN] if use_xvfb else [OPENSCAD_BIN]
    # Render PNG preview
    subprocess.run(
        cmd_prefix + ["--imgsize=800,600", "--autocenter", "--viewall", "-o", png_path, scad_path],
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
    allow_credentials=True,
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


@app.post("/refine")
async def refine(request: RefineRequest):
    name = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scad_path = f"{base}/models/{name}.scad"
    png_path = f"{base}/outputs/{name}.png"
    stl_path = f"{base}/outputs/{name}.stl"

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
    """Image → 3D Model using Ollama vision model."""
    image_data = await file.read()
    image_base64 = base64.b64encode(image_data).decode()

    # Step 1: Vision LLM — describe image
    description = ollama_vision(
        image_base64,
        "Describe this object in 1 sentence for 3D modeling. Focus on shape, size, key features."
    )

    # Step 2: Check SHAPES library first
    scad_code = find_shape_in_library(description)

    if not scad_code:
        # Use Ollama for unknown shapes
        scad_code = ollama_generate(
            "Generate simple valid OpenSCAD code. STRICT RULES: "
            "1) Use ONLY these functions: cube(), sphere(), cylinder(), translate(), union(){} "
            "2) NO variables 3) NO loops 4) NO comments "
            "5) union() uses curly braces {} only 6) Maximum 10 lines "
            "7) Return ONLY the OpenSCAD code. Object: " + description
        )
    scad_code = sanitize_scad(scad_code)

    # Step 3: Render
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
        return {"error": "No STL file found"}
    latest = max(files, key=os.path.getctime)
    return FileResponse(latest, filename="model.stl", media_type="application/octet-stream")


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