import os
import time
import json
import re
import base64
import traceback
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# Optional clients
genai = None
try:
    from google import genai
except ImportError:
    pass

InferenceClient = None
try:
    from huggingface_hub import InferenceClient
except ImportError:
    pass

openai = None
try:
    import openai
except ImportError:
    pass

load_dotenv()

# --- Configuration ---
GEMINI_MODELS = [
    "gemini-2.0-flash-lite", 
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]

MAX_RETRIES = 2
RETRY_BASE_DELAY = 2 # seconds

# --- Client Initializations ---
def get_gemini_client():
    if not genai: return None
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None

def get_hf_client():
    if not InferenceClient: return None
    token = os.getenv("HF_TOKEN")
    if not token: return None
    try:
        return InferenceClient(api_key=token)
    except Exception:
        return None

def get_openai_client():
    if not openai: return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: return None
    try:
        return openai.OpenAI(api_key=api_key)
    except Exception:
        return None

# --- Helpers ---
def encode_image(image: Image.Image) -> str:
    """Convert PIL image to base64 string."""
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def extract_json(text: str) -> dict:
    """Robustly extract JSON from a string that might contain other text."""
    try:
        # Match from the first '{' to the last '}'
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            clean_json = match.group(0)
            # Remove potential markdown fences
            clean_json = re.sub(r'```json\s*|\s*```', '', clean_json).strip()
            return json.loads(clean_json)
    except Exception as e:
        print(f"JSON extraction failed: {e}")
    return None

def ai_generate(prompt, image=None, response_mime_type=None):
    """
    Core AI calling function with:
    1. Gemini rotation & retries with exponential backoff.
    2. Fallback to HF Vision.
    3. Fallback to OpenAI Vision.
    """
    
    # 1. Try Gemini
    gemini_client = get_gemini_client()
    if gemini_client:
        for model_id in GEMINI_MODELS:
            for attempt in range(MAX_RETRIES):
                try:
                    contents = [prompt, image] if image else prompt
                    config = {}
                    if response_mime_type:
                        try:
                            # Try modern format for google-genai
                            from google.genai import types
                            config = types.GenerateContentConfig(response_mime_type=response_mime_type)
                        except ImportError:
                            # Fallback to dict
                            config = {'response_mime_type': response_mime_type}
                    
                    resp = gemini_client.models.generate_content(
                        model=model_id, 
                        contents=contents,
                        config=config if config else None
                    )
                    # If using modern SDK it might have thought logic warning, we use text
                    return resp.text.strip()
                except Exception as e:
                    err_str = str(e).lower()
                    is_rate_limit = any(k in err_str for k in ["429", "resource_exhausted", "quota", "rate"])
                    
                    if is_rate_limit:
                        if attempt < MAX_RETRIES - 1:
                            wait_time = RETRY_BASE_DELAY * (2 ** attempt)
                            print(f"[AI Service] {model_id} rate limited. Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            print(f"[AI Service] {model_id} quota exhausted.")
                    else:
                        print(f"[AI Service] {model_id} unexpected error: {e}")
                    
                    # Instead of breaking loop on another error, let it try the next model
                    break

    # 2. Fallback to HF
    hf_client = get_hf_client()
    if hf_client:
        try:
            print("[AI Service] Falling back to Hugging Face...")
            messages = []
            if image:
                img_b64 = encode_image(image)
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }]
                model = "unsloth/Llama-3.2-11B-Vision-Instruct"
            else:
                messages = [{"role": "user", "content": prompt}]
                model = "mistralai/Mistral-7B-Instruct-v0.3"

            resp = hf_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1500
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[AI Service] HF Fallback failed: {e}")

    # 3. Fallback to OpenAI
    openai_client = get_openai_client()
    if openai_client:
        try:
            print("[AI Service] Falling back to OpenAI...")
            messages = []
            if image:
                img_b64 = encode_image(image)
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }]
                model = "gpt-4o-mini"
            else:
                messages = [{"role": "user", "content": prompt}]
                model = "gpt-3.5-turbo"

            resp = openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1500
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[AI Service] OpenAI Fallback failed: {e}")

    return "__OFFLINE__"
