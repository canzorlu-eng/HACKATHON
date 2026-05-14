"""
List embedding-capable Gemini models accessible to the configured API key.

Run from anywhere — loads GEMINI_API_KEY from the project-root .env:
    python -m scripts.list_embed_models

Prints one model name per line. Pick one and set it as EMBEDDING_MODEL in .env.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env", override=False)
except ImportError:
    pass

import os

api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    print("[ERROR] GEMINI_API_KEY not set in .env", file=sys.stderr)
    sys.exit(1)

import google.generativeai as genai
genai.configure(api_key=api_key)

print("Embedding-capable models available to your key:\n")
found = False
for model in genai.list_models():
    methods = list(getattr(model, "supported_generation_methods", []) or [])
    if "embedContent" in methods:
        # Strip the "models/" prefix so the value can be dropped straight
        # into EMBEDDING_MODEL=... in .env.
        short = model.name.split("/", 1)[-1]
        print(f"  {short:40s}  (input: {model.input_token_limit} tokens)")
        found = True

if not found:
    print("  (none — your key has no embedding access)", file=sys.stderr)
    sys.exit(2)
