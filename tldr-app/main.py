from pathlib import Path
import json
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from llm_client import generate as ollama_generate

app = FastAPI(title="Terms Long; Didn't Read - TL;DR")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    obligations: list[str]
    required_data: list[str]
    deadlines: list[str]
    applies_to: list[str]
    unclear_points: list[str]

@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    full_prompt = f"""
You are a compliance and policy summarisation assistant.

Read the text and return ONLY valid JSON with this exact structure:

{{
  "obligations": ["..."],
  "required_data": ["..."],
  "deadlines": ["..."],
  "applies_to": ["..."],
  "unclear_points": ["..."]
}}

Rules:
- obligations: list the key duties, obligations, or required actions.
- required_data: list documents, data, evidence, or information required.
- deadlines: list timing requirements, due dates, renewal periods, or frequency obligations.
- applies_to: list who the rule, policy, or obligation appears to apply to.
- unclear_points: list anything ambiguous, missing, or not clearly specified.
- Use short, practical bullet-style strings.
- If a section has nothing clear, return an empty list.
- Do not include markdown.
- Do not include any text before or after the JSON.

Text:
{req.prompt}
""".strip()
    
    llm_output = ollama_generate(full_prompt)
    print("RAW MODEL OUTPUT:", llm_output)
    
try:
    match = re.search(r'\{.*\}', llm_output, re.DOTALL)
    if not match:
        raise HTTPException(
            status_code=500,
            detail="Model did not return valid JSON."
        )
    data = json.loads(match.group())
except json.JSONDecodeError:
    raise HTTPException(
        status_code=500,
        detail="Model did not return valid JSON."
    )
