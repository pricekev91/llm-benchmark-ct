# backend/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional


# --- Endpoint Config ---
class EndpointConfigSchema(BaseModel):
    id: str = Field(description="Unique identifier for the endpoint.")
    name: str = Field(description="User-friendly name.")
    base_url: str = Field(description="Base URL of the API endpoint.")
    provider: str = Field(default="OpenAI", description="Provider type (OpenAI, llama.cpp, LiteLLM, llama-swap, vLLM).")
    api_key: str = Field(default="", description="Optional API key for this endpoint.")


# --- Model Config ---
class ModelConfigSchema(BaseModel):
    id: str
    name: str = Field(description="Model name (e.g., GPT-4o, Llama-3-8B).")
    provider: str = Field(description="Provider name.")


# --- Prompt Preset ---
class PromptPresetSchema(BaseModel):
    id: str
    name: str
    template: str
    category: str = Field(default="general")


# --- Benchmark Request ---
class BenchmarkRunRequest(BaseModel):
    model_id: str = Field(description="ID of the selected model.")
    endpoint_id: str = Field(description="ID of the target endpoint.")
    prompt_text: str = Field(description="The prompt to be tested.")
    max_tokens: int = Field(default=1024, description="Maximum output tokens.")
    model_name: Optional[str] = Field(default=None, description="Override model name for the adapter.")


# --- Benchmark Result ---
class BenchmarkResult(BaseModel):
    run_id: str
    model_name: str
    endpoint_id: str
    latency_ms: float
    tokens_generated: int
    status: str = "completed"


# --- History Filter ---
class HistoryFilterSchema(BaseModel):
    model_name: Optional[str] = None
    endpoint_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: Optional[int] = 100
