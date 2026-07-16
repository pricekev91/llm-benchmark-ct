from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "phase": 0}

@app.get("/health")
async def health():
    return {"status": "ok"}
