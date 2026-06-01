from fastapi import FastAPI
from groq import Groq
import os
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import re
import base64
from datetime import datetime
import os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class PromptRequest(BaseModel):
    prompt: str

class RefineRequest(BaseModel):
    previous_scad: str
    instruction: str

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
}

def find_shape(prompt: str) -> str:
    prompt_lower = prompt.lower()
    for key in SHAPES:
        if key in prompt_lower:
            return SHAPES[key]
    groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": "Generate simple OpenSCAD code using ONLY cube(), sphere(), cylinder(), translate(), union(). NO variables. NO loops. Return ONLY code. For: " + prompt}],
        max_tokens=500
    )
    code = response.choices[0].message.content.strip()
    code = re.sub(r'```[a-zA-Z]*', '', code)
    code = code.replace('```', '').strip()
    for keyword in ['union','difference','cube','cylinder','sphere','translate']:
        if keyword in code:
            code = code[code.find(keyword):]
            break
    return code

def render(scad_code, scad_path, png_path, stl_path):
    with open(scad_path, "w") as f:
        f.write(scad_code)
    subprocess.run(["openscad","--imgsize=800,600","--autocenter","--viewall","-o",png_path,scad_path], capture_output=True)
    subprocess.run(["openscad","-o",stl_path,scad_path], capture_output=True)

@app.post("/generate")
async def generate(request: PromptRequest):
    name = datetime.now().strftime("%Y%m%d_%H%M%S")
    scad_path = f"/home/sandra/3d_model_generator/models/{name}.scad"
    png_path = f"/home/sandra/3d_model_generator/outputs/{name}.png"
    stl_path = f"/home/sandra/3d_model_generator/outputs/{name}.stl"
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
    scad_path = f"/home/sandra/3d_model_generator/models/{name}.scad"
    png_path = f"/home/sandra/3d_model_generator/outputs/{name}.png"
    stl_path = f"/home/sandra/3d_model_generator/outputs/{name}.stl"

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

    groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": system_prompt}],
        max_tokens=500
    )
    code = response.choices[0].message.content.strip()
    code = re.sub(r'```[a-zA-Z]*', '', code)
    code = code.replace('```', '').strip()
    for keyword in ['union','difference','cube','cylinder','sphere','translate']:
        if keyword in code:
            code = code[code.find(keyword):]
            break

    # fallback — previous_scad use ചെയ്യൂ
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
    stl_path = f"/home/sandra/3d_model_generator/outputs/{filename}.stl"
    if os.path.exists(stl_path):
        return {"stl_path": stl_path, "status": "success"}
    return {"error": "File not found"}

@app.get("/")
async def root():
    return {"message": "3D Model Generator API Running!"}

@app.post("/route")
async def route(request: PromptRequest):
    """Router — parametric or ai_generator decide ചെയ്യുന്നു"""
    prompt_lower = request.prompt.lower()
    
    # Parametric keywords
    parametric_keywords = [
        'box', 'cube', 'sphere', 'cylinder', 'cone', 'chair', 'table',
        'house', 'rocket', 'snowman', 'tree', 'car', 'bottle', 'trophy',
        'mushroom', 'cat', 'mm', 'cm', 'height', 'width', 'radius',
        'geometric', 'simple', 'basic'
    ]
    
    # AI keywords  
    ai_keywords = [
        'realistic', 'organic', 'animal', 'person', 'face', 'dragon',
        'complex', 'detailed', 'artistic', 'sculpture', 'photo'
    ]
    
    parametric_score = sum(1 for k in parametric_keywords if k in prompt_lower)
    ai_score = sum(1 for k in ai_keywords if k in prompt_lower)
    
    if ai_score > parametric_score:
        path = "ai_generator"
    else:
        path = "parametric"
    
    return {
        "prompt": request.prompt,
        "path": path,
        "parametric_score": parametric_score,
        "ai_score": ai_score
    }

from fastapi import UploadFile, File
import base64

@app.post("/generate_from_image")
async def generate_from_image(file: UploadFile = File(...)):
    import os
    from groq import Groq
    
    # Read image
    image_data = await file.read()
    image_base64 = base64.b64encode(image_data).decode()
    
    groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    
    # Step 1: Vision LLM — describe image
    vision_response = groq_client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                {"type": "text", "text": "Describe this object in 1 sentence for 3D modeling. Focus on shape, size, key features."}
            ]
        }],
        max_tokens=100
    )
    description = vision_response.choices[0].message.content.strip()
    
    # Step 2: Generate OpenSCAD
    scad_response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": f"Generate simple OpenSCAD code using ONLY cube(), sphere(), cylinder(), translate(), union(). NO variables. NO loops. Return ONLY code. For: {description}"}],
        max_tokens=500
    )
    scad_code = scad_response.choices[0].message.content.strip()
    import re
    scad_code = re.sub(r'```[a-zA-Z]*', '', scad_code).replace('```', '').strip()
    for keyword in ['union','difference','cube','cylinder','sphere','translate']:
        if keyword in scad_code:
            scad_code = scad_code[scad_code.find(keyword):]
            break
    
    # Step 3: Render
    from datetime import datetime
    name = datetime.now().strftime("%Y%m%d_%H%M%S")
    scad_path = f"/app/models/{name}.scad"
    png_path = f"/app/outputs/{name}.png"
    stl_path = f"/app/outputs/{name}.stl"
    
    import subprocess
    with open(scad_path, "w") as f:
        f.write(scad_code)
    subprocess.run(["openscad","--imgsize=800,600","--autocenter","--viewall","-o",png_path,scad_path], capture_output=True)
    subprocess.run(["openscad","-o",stl_path,scad_path], capture_output=True)
    
    import os
    if not os.path.exists(png_path):
        return {"error": "Render failed", "description": description, "scad_code": scad_code}
    
    with open(png_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode()
    
    return {
        "description": description,
        "scad_code": scad_code,
        "image": img_base64,
        "status": "success"
    }
