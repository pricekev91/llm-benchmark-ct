from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED
from .auth import verify_api_key
import os

# Initialize FastAPI application
app = FastAPI(title="LLM Benchmark API")

# Placeholder for initialization logic (e.g., connecting to DB)
def initialize_db():
    print("DB Initialization Stub: Checking SQLite connection...")
    # db.py will handle actual initialization later
    pass

# Run DB init upon startup
initialize_db()

@app.on_event("startup")
def startup_event():
    pass

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "llm-benchmark-ct"}

@app.middleware("http")
async def authenticate_middleware(request, call_next):
    """Middleware to enforce API key authentication."""
    api_key = request.headers.get("X-API-KEY")
    if not verify_api_key(api_key):
        return JSONResponse(
            status_code=HTTP_401_UNAUTHORIZED,
            content={"error": "Unauthorized", "detail": "Invalid or missing API Key"},
        )
    return await call_next(request)

# --- Stub Routes ---

# Example endpoint for saving configuration
@app.post("/endpoints/save")
def save_endpoint():
    return {"message": "Endpoint saved stubbed", "status": "success"}

# Example endpoint for listing configurations
@app.get("/endpoints/list")
def list_endpoints():
    return {"endpoints": [], "message": "Listing endpoints stubbed"}

# Example endpoint for listing available models
@app.get("/models/list")
def list_models():
    return {"models": ["OpenAI-GPT4", "Claude-3"], "message": "Listing models stubbed"}

# Example endpoint for running a benchmark
@app.post("/benchmark/run")
def run_benchmark():
    return {"message": "Benchmark run initiated stubbed", "status": "processing"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
