from fastapi import FastAPI
from pydantic import BaseModel

from llm_client import generate as ollama_generate

app = FastAPI()

class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    text: str

@app.get("/")
async def root():
    return {"message": "Terms Long; Didn't Read"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    full_prompt = (
    "Summarise the following text into the 3–5 main points, "
    "focusing on obligations and data required:\n\n"
    f"{req.prompt}"
    )
    llm_output = ollama_generate(full_prompt)
    return GenerateResponse(text=llm_output)
