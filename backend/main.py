# backend/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.status import HTTP_401_UNAUTHORIZED
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import verify_api_key, is_public_path
from .db import initialize_database

import os

# Initialize FastAPI application
app = FastAPI(title="LLM Benchmark API", version="1.0.0")

# --- Startup ---
@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    initialize_database()


# --- Auth Middleware ---
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow public paths without auth
        if is_public_path(path):
            return await call_next(request)

        api_key = request.headers.get("X-API-KEY")
        if not verify_api_key(api_key):
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={"error": "Unauthorized", "detail": "Invalid or missing API Key"},
            )
        return await call_next(request)


app.add_middleware(AuthMiddleware)


# --- Health Check (public) ---
@app.get("/health")
def health_check():
    """Health check endpoint — no auth required."""
    return {"status": "ok", "service": "llm-benchmark-ct"}


# --- Include Routers (protected by middleware) ---
from .endpoints import config_router, preset_router, benchmark_router, analytics_router

app.include_router(config_router)
app.include_router(preset_router)
app.include_router(benchmark_router)
app.include_router(analytics_router)


# --- Serve Frontend (public) ---
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")


@app.get("/")
async def serve_frontend():
    """Serve the main frontend page — no auth required."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        status_code=503,
        content={"error": "Frontend not built. Run the build step."},
    )


# Mount static files for JS/CSS/assets
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
