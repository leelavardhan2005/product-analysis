
title: Purepic
---

# PurePic: Smart Nutrition & Health AI 🥦🧠

**PurePic** is a next-generation clinical health assistant and optical product scanner. It leverages state-of-the-art Deep Learning models to extract complex nutritional data from physical food labels and provides highly customized dietary recommendations mapped directly to a user’s unique medical profile.

---

## 🚀 The Deep Learning Core (Image-to-Text Extraction)

PurePic does not rely on traditional, error-prone Optical Character Recognition (OCR) libraries (like Tesseract). Standard OCR fails when reading curved bottles, crumpled wrappers, or inconsistent lighting. Instead, PurePic utilizes **Google's Gemini 1.5 / 2.0 Flash**, a highly optimized **Multimodal Large Language Model (MLLM)**.

### How The Extraction Works (Theoretical Concepts)

1. **Vision Transformers (ViT):**
   When an image of a nutrition label is uploaded, the image is fragmented into patches and passed through a Vision Transformer (ViT). Unlike convolutional neural networks (CNNs), the ViT uses a **self-attention mechanism** to understand the spatial relationships between tokens (e.g., visually associating the string "20g" with the header "Total Fat" even if they are far apart in the image).

2. **Multimodal Alignment:**
   The dense vectors produced by the Vision Transformer are projected into the same latent space as text embeddings. This alignment allows the core LLM to "read" the image semantically, rather than just transcribing characters blindly.

3. **Structured Generation (JSON Schema Enforcement):**
   Once the model understands the label visually, we execute a highly specific System Prompt that enforces JSON parsing. The Language Model decodes the visual tokens and outputs a highly structured JSON dictionary containing:
   - Evaluated safety heuristics (SAFE, CAUTION, AVOID)
   - Extrapolated Macronutrients & Micronutrients
   - Individual ingredient profiling (e.g., flagging 'Red 40' as HARMFUL)

### Conversational Memory (RAG-like Context Injection)
The **Nova Dietary Concierge** chatbot functions via dynamic prompt injection. During conversations, Nova is injected with the user's SQLite-stored Medical Profile (including constraints like IBS or Pregnancy) alongside the parsed JSON of the scanned product, allowing the inference engine to generate highly customized, context-aware dietary responses.

---

## 🛠️ The Tech Stack

PurePic is built using a modern, lightweight, and robust Python stack designed for rapid AI deployment:

### 1. Frontend Interface & UI Routing
* **Framework:** Gradio (v3 / v4 / v5 / v6 compatibility architecture)
* **Design Philosophy:** Single Page Application (SPA). Instead of using standard Gradio pages, we utilize a custom `gr.Tabs` engine driven by hidden Python state logic to achieve instantaneous "App-Like" screen transitions.
* **Styling:** Injected raw HTML and aggressive Custom CSS (`CSS = """..."""`) using modern aesthetics (Inter fonts, glassmorphism, dynamic accent colors `#f97316`).

### 2. Backend Orchestration & API Runtime
* **Language:** Python 3.10+
* **Deep Learning Interface:** `google-genai` (SDK) to interface directly with Google's TPU clusters running Gemini Multimodal models.
* **Fault Tolerance Loop:** To circumvent rate limits, the API router executes a fallback loop iterating between `gemini-2.5-flash`, `gemini-2.0-flash-lite`, and `gemini-2.5-pro`.

### 3. Database Architecture (Entity Management)
* **System:** SQLite (`users.db`)
* **Persistence strategy:** We utilize Python's built-in `sqlite3` library configured with `PRAGMA journal_mode=WAL` (Write-Ahead Logging) to ensure threaded concurrency without "database is locked" crashes.
* **Data Flow:** Passwords and usernames are stored using lightweight hashing, while dynamic clinical profiles (Height, Weight, Medical Constraints) are aggressively condensed into a standard JSON string payload (`profile_json`) for infinite flexibility within the relational store.

### 4. Cloud Deployment (Hosting)
* **Provider:** Hugging Face Spaces (Docker environment)
* **Environment:** Hugging Face spins up an ephemeral Docker container containing the Gradio node server, fetching secrets securely at runtime. (Note: The `users.db` is ephemeral unless 'Persistent Storage' is enabled in the HF UI to persist the `/data` tier).

---

## 📦 How to Run Locally

1. **Clone the repository.**
2. **Install core requirements:** `pip install -r requirements.txt` (or specifically: `gradio google-genai pillow python-dotenv`).
3. **Setup Secrets:** Create a `.env` file in the root directory and add your key:
   ```env
   GEMINI_API_KEY=your_google_key_here
   ```
4. **Boot the Server:** Run `python app.py`
5. Visit `http://localhost:7860` in any web browser!

---
*Developed as a premier AI healthcare software tool integrating modern machine learning pipelines into consumer UX.*
