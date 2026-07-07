# 🧊 LLM-Based 3D Model Generator

A web application that generates 3D models from text descriptions and images.

## 🌐 Live Demo
- **Frontend:** https://frontend-mocha-three-73.vercel.app
- **Backend:** https://3d-model-generator-production.up.railway.app

## ✨ Features
- 📐 **Text to 3D Generation:** Intent-driven 3D object construction.
- 🧠 **Image to 3D Model:** Computer vision analysis powered by Groq Vision (Llama 3.2/3.1).
- 🔧 **Refinement Controls:** Iterative adjustments (bigger, taller, smaller, etc.).
- ⬇️ **STL Export:** Production-ready downloads optimized for 3D printing.

## 🛠️ Tech Stack
- **Frontend:** Next.js, TailwindCSS, Vercel
- **Backend:** Python, FastAPI, Railway
- **LLM/Vision:** Groq API (Llama 3.1 / Vision models)
- **3D Engine:** OpenSCAD

---

## 🤖 LLM Architecture & Cost Quality 

This application leverages an optimized hybrid generation pipeline designed to balance computational costs, latency, and asset complexity.

### 1. Intent Routing & Scoring (Cost Management)
Instead of processing simple geometric shapes through expensive multi-view diffusion or generative models, the backend uses a custom intent-scoring router:
* **Parametric Engine (Near-Zero Cost):** Prompts containing explicit metrics or structural geometries (e.g., *"a simple box 20mm wide"*) are routed to programmatic OpenSCAD generators.
* **AI Engine (High Fidelity):** Complex, organic, or abstract commands (e.g., *"a realistic organic dragon"*) bypass basic generators and trigger deep LLM parsing via Groq.

---

## ⚙️ Engineering Practice & CI/CD 

We maintain strict test-driven isolation and code quality metrics.
* **Automated Testing Suite:** Powered by `pytest` and `FastAPI TestClient`. Six core test modules natively validate route orchestration, string safety, and asset parsing maps.
* **CI/CD Pipeline:** Configured via GitHub Actions (`.github/workflows/ci.yml`). Every codebase push triggers automated sandbox building, dependency isolation, and regression verification steps.

```bash
# To run the test suite locally:
source venv/bin/activate
pytest tests/

## 🛡️ Innovation, Ethics, & Safety Guardrails

This project is built with a strong focus on engineering ethics, user data privacy, and foundational LLM safety patterns.

### 1. Input Safety & Content Moderation
* **Structural Intent Filters:** System prompts explicitly instruct the Groq LLM layer to reject requests attempting to generate dangerous materials, weapons, or explicit intellectual property.
* **Fallback Degradation:** If an invalid, unsafe, or malformed generation request passes the initial boundary, the backend router naturally routes to a safe, pre-calculated geometry standard (e.g., standard fallback primitive shapes) rather than executing unpredictable string generations.

### 2. Algorithmic Bias Mitigation
* **Style Diversity Injection:** Standard prompts are automatically enriched with grounding tokens behind the scenes. This ensures that abstract generic descriptions (e.g., "a house" or "a chair") output structurally diverse, globally representative geometric parameters rather than defaulting to single regional cultural biases.

### 3. Data Privacy & Secrets Management
* **Zero-Log Input Processing:** User-uploaded vision files and conversational text prompts are processed ephemerally. Images are transmitted directly to the Groq Vision cloud infrastructure over encrypted HTTPS paths and are completely purged from backend session environments post-rendering.
* **Commit Ledger Security:** Full repository sanitation was performed using automated commit filters to permanently expunge active runtime secrets from tracking trees, ensuring cloud infrastructure API keys remain entirely managed via secure Railway and Vercel container variables.

