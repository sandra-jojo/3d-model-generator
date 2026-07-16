# 3D Model Generator — Video Presentation Script
# Duration: ~3 min 45 sec | Words: ~560
# Pace: ~150 words/min (natural speaking speed)

================================================================
VISUAL LEGEND:
  [SCREEN] = Show this on screen (screen recording / slide / demo)
  [CAMERA] = Talk to camera (face shots)
  [TEXT]   = Text overlay on screen
================================================================

---

[0:00 — 0:25] INTRO
---------------------

[CAMERA]
"Have you ever wanted to turn a simple text description or a photo into a real 3D printable model? That's exactly what our 3D Model Generator does."

[SCREEN — Show live app: https://frontend-mocha-three-73.vercel.app]
[TEXT: "3D Model Generator — Text & Image to 3D"]

[CAMERA]
"I'm going to walk you through how it works, what technologies power it, and a live demo — all in under 4 minutes."

---

[0:25 — 0:55] THE PROBLEM & SOLUTION
--------------------------------------

[CAMERA]
"In 3D printing, the biggest bottleneck is design. Professional CAD software like Fusion 360 or Blender takes months to learn. Most people just want a simple shape — a box, a gear, a vase — but they don't know how to model it."

[SCREEN — Show someone struggling with Blender UI, then switch to our clean web UI]
[TEXT: "Problem: 3D modeling is hard. Solution: AI does it for you."]

[CAMERA]
"Our solution is a web app where you simply type what you want — like 'snowman' or 'a futuristic spaceship' — or upload a photo, and the system generates a 3D model you can download as an STL file and send straight to your 3D printer."

---

[0:55 — 1:35] ARCHITECTURE — HOW IT WORKS
-------------------------------------------

[SCREEN — Show architecture diagram]

[CAMERA]
"The app has four main components."

[TEXT overlay on diagram as each is mentioned:]

"First — the Frontend. A Next.js web app built with React and TailwindCSS. This is what the user sees and interacts with. It's hosted on Vercel."

"Second — the Backend. A Python FastAPI server running on Railway. It has 14 API endpoints handling everything from text generation to image processing to cloud API calls."

"Third — the AI Engine. We use Ollama running locally with two models: GLM4 for text-to-code generation, and llama3.2-vision for understanding images. This is completely free — zero API costs."

"Fourth — OpenSCAD. An open-source 3D CAD tool that takes code and renders it into a 3D model. It produces both a PNG preview image and an STL file for 3D printing."

---

[1:35 — 2:15] DEMO — TEXT TO 3D
----------------------------------

[SCREEN — Live demo on homepage]

[CAMERA]
"Let me show you a live demo. I'll type 'snowman' and click Generate."

[SCREEN — Type "snowman", click Generate, wait for preview]

[CAMERA]
"Behind the scenes, the backend first checks a built-in library of 19 common shapes. 'Snowman' is in there, so it returns the OpenSCAD code instantly — no AI needed. OpenSCAD renders the 3D model and we get a preview image plus a downloadable STL file."

[SCREEN — Show the preview image appearing, click Download STL]

[CAMERA]
"Now let's try something not in the library — 'a futuristic spaceship'."

[SCREEN — Type "a futuristic spaceship", click Generate]

[CAMERA]
"This time, the backend sends the prompt to the Ollama AI model, which generates OpenSCAD code. Our sanitizer function cleans up any errors in the AI output, and OpenSCAD renders it. We get a unique 3D model that was never hardcoded — the AI created it from scratch."

---

[2:15 — 2:45] DEMO — IMAGE TO 3D
-----------------------------------

[SCREEN — Switch to Image -> 3D mode]

[CAMERA]
"Now let's try image-to-3D. I upload a photo of a chair."

[SCREEN — Upload chair photo, click Generate]

[CAMERA]
"The image goes to the llama3.2-vision model, which describes what it sees — 'a wooden chair with four legs.' The system matches that to the shape library, renders it, and we have a 3D model from a photo. You can also refine it — type 'make it bigger' and the AI modifies the code."

---

[2:45 — 3:15] MORE FEATURES
------------------------------

[SCREEN — Quick tour of other pages]

[CAMERA]
"Beyond the local AI engine, we have three more generation options."

[SCREEN — Show /cloud page]
"The Cloud page connects to Meshy AI and Tripo AI — paid APIs that produce high-quality textured meshes in formats like GLB, FBX, and OBJ."

[SCREEN — Show /huggingface page]
"The HuggingFace page uses free Spaces like TripoSR and Hunyuan3D for medium-quality 3D generation at zero cost."

[SCREEN — Show /parametric page, adjust a slider, generate]
"And the Parametric page offers 10 customizable templates — like this adjustable box. You change the width, height, and wall thickness with sliders, and OpenSCAD generates the exact model in real-time."

---

[3:15 — 3:45] CONCLUSION
--------------------------

[CAMERA]
"To summarize — our 3D Model Generator turns text and images into 3D printable models using a local AI engine, cloud APIs, and parametric templates. It runs on Railway and Vercel, uses Ollama for free local AI, and outputs STL files ready for any 3D printer."

[SCREEN — Show the live app one more time with a generated model]
[TEXT: "GitHub: github.com/sandra-jojo/3d-model-generator"]

[CAMERA]
"This is the foundation of FOFUS, our AI-powered 3D printing business. Thank you for watching."

[TEXT: "Thank you — Questions?"]

---

END OF SCRIPT
Total spoken words: ~560
Estimated duration: 3 min 45 sec