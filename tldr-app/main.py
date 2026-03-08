from fastapi import FastAPI
from pydantic import BaseModel

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
    # TODO: replace this with a real LLM call
    fake_output = f"Generated response for: {req.prompt}"
    return GenerateResponse(text=fake_output)
