"""
Parametric 3D Model Templates
Each template is a function that returns OpenSCAD code given parameters.
"""
import os
import re
import subprocess
import base64
import tempfile
from datetime import datetime

OPENSCAD_BIN = os.path.expanduser("~/openscad/openscad-2021.01/openscad.exe")
if not os.path.exists(OPENSCAD_BIN):
    import shutil
    if shutil.which("openscad"):
        OPENSCAD_BIN = "openscad"

TEMPLATES = {
    "adjustable_box": {
        "name": "Adjustable Box",
        "category": "Enclosures",
        "description": "A simple parametric box with optional lid",
        "parameters": [
            {"name": "width", "type": "number", "default": 50, "min": 10, "max": 200, "unit": "mm"},
            {"name": "depth", "type": "number", "default": 50, "min": 10, "max": 200, "unit": "mm"},
            {"name": "height", "type": "number", "default": 30, "min": 10, "max": 200, "unit": "mm"},
            {"name": "wall_thickness", "type": "number", "default": 2, "min": 0.8, "max": 5, "unit": "mm"},
            {"name": "has_lid", "type": "boolean", "default": True},
        ],
        "scad": """difference() {
  cube([@@width@@, @@depth@@, @@height@@]);
  translate([@@wall_thickness@@, @@wall_thickness@@, @@wall_thickness@@])
    cube([@@width@@ - 2*@@wall_thickness@@, @@depth@@ - 2*@@wall_thickness@@, @@height@@]);
}
@@lid_scad@@""",
    },
    "rounded_box": {
        "name": "Rounded Box",
        "category": "Enclosures",
        "description": "A box with rounded corners",
        "parameters": [
            {"name": "width", "type": "number", "default": 60, "min": 10, "max": 200, "unit": "mm"},
            {"name": "depth", "type": "number", "default": 40, "min": 10, "max": 200, "unit": "mm"},
            {"name": "height", "type": "number", "default": 25, "min": 5, "max": 100, "unit": "mm"},
            {"name": "radius", "type": "number", "default": 5, "min": 1, "max": 20, "unit": "mm"},
            {"name": "wall_thickness", "type": "number", "default": 2, "min": 0.8, "max": 5, "unit": "mm"},
        ],
        "scad": """module rounded_box(w, d, h, r) {
  hull() {
    translate([r, r, 0]) cylinder(r=r, h=h);
    translate([w-r, r, 0]) cylinder(r=r, h=h);
    translate([r, d-r, 0]) cylinder(r=r, h=h);
    translate([w-r, d-r, 0]) cylinder(r=r, h=h);
  }
}
difference() {
  rounded_box(@@width@@, @@depth@@, @@height@@, @@radius@@);
  translate([@@wall_thickness@@, @@wall_thickness@@, @@wall_thickness@@])
    rounded_box(@@width@@ - 2*@@wall_thickness@@, @@depth@@ - 2*@@wall_thickness@@, @@height@@, max(@@radius@@ - @@wall_thickness@@, 0.5));
}""",
    },
    "gear": {
        "name": "Spur Gear",
        "category": "Mechanical",
        "description": "A simple involute gear",
        "parameters": [
            {"name": "teeth", "type": "number", "default": 20, "min": 6, "max": 100, "unit": "count"},
            {"name": "module", "type": "number", "default": 2, "min": 0.5, "max": 10, "unit": "mm"},
            {"name": "thickness", "type": "number", "default": 5, "min": 1, "max": 30, "unit": "mm"},
            {"name": "hole_radius", "type": "number", "default": 3, "min": 0, "max": 20, "unit": "mm"},
        ],
        "scad": """module gear(teeth, m, thickness, hole_r) {
  outer_r = teeth * m / 2 + m;
  inner_r = teeth * m / 2 - m * 0.6;
  difference() {
    cylinder(r=outer_r, h=thickness, $fn=teeth*2);
    for (i = [0:teeth-1]) {
      rotate([0, 0, i * 360 / teeth])
        translate([outer_r - m*0.3, 0, -1])
        cylinder(r=m*0.5, h=thickness+2, $fn=3);
    }
    if (hole_r > 0)
      cylinder(r=hole_r, h=thickness+2, center=true);
  }
}
gear(@@teeth@@, @@module@@, @@thickness@@, @@hole_radius@@);""",
    },
    "vase": {
        "name": "Spiral Vase",
        "category": "Home & Living",
        "description": "A decorative spiral vase",
        "parameters": [
            {"name": "height", "type": "number", "default": 80, "min": 30, "max": 200, "unit": "mm"},
            {"name": "base_radius", "type": "number", "default": 15, "min": 5, "max": 40, "unit": "mm"},
            {"name": "top_radius", "type": "number", "default": 25, "min": 5, "max": 50, "unit": "mm"},
            {"name": "twist", "type": "number", "default": 90, "min": 0, "max": 360, "unit": "degrees"},
            {"name": "wall_thickness", "type": "number", "default": 1.5, "min": 0.8, "max": 5, "unit": "mm"},
        ],
        "scad": """module vase(h, r_base, r_top, twist_deg, wt) {
  difference() {
    linear_extrude(height=h, twist=twist_deg, slices=40, $fn=64)
      circle(r=r_base);
    translate([0, 0, -1])
      linear_extrude(height=h+2, twist=twist_deg, slices=40, $fn=64)
      circle(r=r_base - wt);
  }
}
vase(@@height@@, @@base_radius@@, @@top_radius@@, @@twist@@, @@wall_thickness@@);""",
    },
    "cable_clip": {
        "name": "Cable Clip",
        "category": "Practical",
        "description": "A cable management clip that screws into a surface",
        "parameters": [
            {"name": "cable_diameter", "type": "number", "default": 6, "min": 2, "max": 20, "unit": "mm"},
            {"name": "base_width", "type": "number", "default": 20, "min": 10, "max": 50, "unit": "mm"},
            {"name": "base_depth", "type": "number", "default": 15, "min": 5, "max": 30, "unit": "mm"},
            {"name": "screw_hole", "type": "number", "default": 4, "min": 2, "max": 8, "unit": "mm"},
        ],
        "scad": """module cable_clip(cable_d, base_w, base_d, screw_d) {
  difference() {
    union() {
      cube([base_w, base_d, 3]);
      translate([base_w/2, base_d/2, 3])
        cylinder(h=cable_d + 5, r=cable_d/2 + 2, $fn=32);
    }
    translate([base_w/2, base_d/2, 3])
      cylinder(h=cable_d + 10, r=cable_d/2, $fn=32);
    translate([base_w/2, 3, 1.5])
      cylinder(h=5, r=screw_d/2, $fn=16);
  }
}
cable_clip(@@cable_diameter@@, @@base_width@@, @@base_depth@@, @@screw_hole@@);""",
    },
    "phone_stand": {
        "name": "Phone Stand",
        "category": "Home & Living",
        "description": "A simple angled phone stand",
        "parameters": [
            {"name": "phone_width", "type": "number", "default": 75, "min": 50, "max": 100, "unit": "mm"},
            {"name": "phone_depth", "type": "number", "default": 8, "min": 5, "max": 15, "unit": "mm"},
            {"name": "stand_height", "type": "number", "default": 50, "min": 30, "max": 100, "unit": "mm"},
            {"name": "angle", "type": "number", "default": 15, "min": 5, "max": 45, "unit": "degrees"},
            {"name": "thickness", "type": "number", "default": 3, "min": 2, "max": 8, "unit": "mm"},
        ],
        "scad": """module phone_stand(pw, pd, sh, ang, t) {
  base_d = sh * sin(ang) + pw * cos(ang);
  difference() {
    union() {
      cube([pw + 2*t, base_d + 10, t]);
      translate([t, 10, 0])
        rotate([ang, 0, 0])
        translate([0, 0, 0])
        cube([pw, sh, t]);
      translate([t, 10 + sh*cos(ang), sh*sin(ang)])
        cube([pw, pd + 2*t, t]);
    }
    translate([t, 10 + sh*cos(ang) - 2, sh*sin(ang) + t])
      cube([pw, pd, t*3]);
  }
}
phone_stand(@@phone_width@@, @@phone_depth@@, @@stand_height@@, @@angle@@, @@thickness@@);""",
    },
    "keychain_tag": {
        "name": "Keychain Tag",
        "category": "Signs & Nameplates",
        "description": "A customizable keychain tag with text",
        "parameters": [
            {"name": "width", "type": "number", "default": 50, "min": 20, "max": 100, "unit": "mm"},
            {"name": "height", "type": "number", "default": 20, "min": 10, "max": 50, "unit": "mm"},
            {"name": "thickness", "type": "number", "default": 3, "min": 1, "max": 10, "unit": "mm"},
            {"name": "text", "type": "string", "default": "FOFUS", "max": 20},
            {"name": "text_size", "type": "number", "default": 8, "min": 3, "max": 15, "unit": "mm"},
            {"name": "hole_radius", "type": "number", "default": 3, "min": 1, "max": 8, "unit": "mm"},
        ],
        "scad": """module keychain_tag(w, h, t, txt, ts, hr) {
  difference() {
    hull() {
      cylinder(r=h/2, h=t);
      translate([w, 0, 0]) cylinder(r=h/2, h=t);
    }
    translate([w/2, 0, 0])
      linear_extrude(height=t+1)
      text(txt, size=ts, halign="center", valign="center");
    translate([8, 0, -1])
      cylinder(r=hr, h=t+2);
  }
}
keychain_tag(@@width@@, @@height@@, @@thickness@@, "@@text@@", @@text_size@@, @@hole_radius@@);""",
    },
    "calibration_cube": {
        "name": "Calibration Cube",
        "category": "3D Printing Aids",
        "description": "A 20mm calibration cube for printer tuning",
        "parameters": [
            {"name": "size", "type": "number", "default": 20, "min": 10, "max": 50, "unit": "mm"},
            {"name": "tolerance_gap", "type": "number", "default": 0.2, "min": 0, "max": 1, "unit": "mm"},
        ],
        "scad": """module cal_cube(s, gap) {
  difference() {
    cube([s, s, s], center=true);
    translate([gap, 0, 0]) cube([s - gap*2, s - gap*2, s - gap*2], center=true);
  }
}
cal_cube(@@size@@, @@tolerance_gap@@);""",
    },
    "ring": {
        "name": "Adjustable Ring",
        "category": "Jewelry",
        "description": "A simple ring with adjustable size and width",
        "parameters": [
            {"name": "inner_diameter", "type": "number", "default": 18, "min": 14, "max": 25, "unit": "mm"},
            {"name": "ring_width", "type": "number", "default": 4, "min": 2, "max": 12, "unit": "mm"},
            {"name": "thickness", "type": "number", "default": 1.5, "min": 0.5, "max": 4, "unit": "mm"},
        ],
        "scad": """module ring(id, w, t) {
  difference() {
    cylinder(r=id/2 + t, h=w, $fn=64);
    translate([0, 0, -1])
      cylinder(r=id/2, h=w+2, $fn=64);
  }
}
ring(@@inner_diameter@@, @@ring_width@@, @@thickness@@);""",
    },
}


def generate_parametric(template_id: str, params: dict, output_dir: str = None):
    """Generate a 3D model from a parametric template.
    Returns dict with scad_code, image (base64), stl_path.
    """
    if template_id not in TEMPLATES:
        return {"error": f"Unknown template: {template_id}"}

    template = TEMPLATES[template_id]

    # Build SCAD code from template
    scad_code = template["scad"]

    # Handle lid for adjustable_box
    if template_id == "adjustable_box":
        has_lid = params.get("has_lid", True)
        lid_scad = ""
        if has_lid:
            w = params.get("width", 50)
            d = params.get("depth", 50)
            wt = params.get("wall_thickness", 2)
            lid_scad = f"""
translate([{w} + 5, 0, 0])
difference() {{
  cube([{w}, {d}, {wt}]);
  translate([{wt}, {wt}, -1])
    cube([{w} - 2*{wt}, {d} - 2*{wt}, {wt} + 2]);
}}"""
        scad_code = scad_code.replace("@@lid_scad@@", lid_scad)

    # Replace parameters using @@name@@ syntax (doesn't conflict with OpenSCAD braces)
    for param in template["parameters"]:
        name = param["name"]
        value = params.get(name, param["default"])
        if param["type"] == "string":
            # Sanitize text — only allow alphanumeric and spaces
            value = re.sub(r'[^a-zA-Z0-9 ]', '', str(value))
        elif param["type"] == "boolean":
            continue  # Booleans are handled by template-specific logic
        else:
            value = float(value) if isinstance(value, (int, float)) else float(param["default"])
        scad_code = scad_code.replace(f"@@{name}@@", str(value))

    # Clean up any remaining @@placeholders@@
    scad_code = re.sub(r'@@\w+@@', '0', scad_code)

    # Render with OpenSCAD
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
    os.makedirs(output_dir, exist_ok=True)

    name = datetime.now().strftime("%Y%m%d_%H%M%S")
    scad_path = os.path.join(output_dir, f"parametric_{name}.scad")
    png_path = os.path.join(output_dir, f"parametric_{name}.png")
    stl_path = os.path.join(output_dir, f"parametric_{name}.stl")

    with open(scad_path, "w") as f:
        f.write(scad_code)

    # Render PNG preview
    subprocess.run(
        [OPENSCAD_BIN, "--imgsize=800,600", "--camera=0,0,0,0,0,0,120", "-o", png_path, scad_path],
        capture_output=True, timeout=60,
    )
    # Export STL
    subprocess.run(
        [OPENSCAD_BIN, "-o", stl_path, scad_path],
        capture_output=True, timeout=60,
    )

    result = {"scad_code": scad_code, "stl_path": stl_path}

    if os.path.exists(png_path):
        with open(png_path, "rb") as f:
            result["image"] = base64.b64encode(f.read()).decode()

    return result