FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Python, OpenSCAD, and Xvfb for headless rendering
RUN apt-get update && apt-get install -y \
    python3 python3-pip openscad xvfb curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p models outputs

# Environment variables with defaults
ENV OLLAMA_BASE_URL=http://localhost:11434/v1
ENV OLLAMA_API_KEY=ollama
ENV OLLAMA_TEXT_MODEL=glm4
ENV OLLAMA_VISION_MODEL=llama3.2-vision

EXPOSE 8000

CMD ["uvicorn", "scripts.api:app", "--host", "0.0.0.0", "--port", "8000"]