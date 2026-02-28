from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Terms Long; Didn't Read"}

@app.get("/health")
async def health():
    return {"status": "ok"}
