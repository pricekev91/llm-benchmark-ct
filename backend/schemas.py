# backend/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

# --- Schemas for Request/Response Validation ---

class EndpointConfigSchema(BaseModel):
    id: str = Field(description="Unique identifier for the endpoint.")
    name: str = Field(description="User-friendly name of the endpoint.")
    base_url: str = Field(description="Base URL of the API endpoint.")

class ModelConfigSchema(BaseModel):
    id: str = Field(description="Unique identifier for the model.")
    name: str = Field(description="Model name (e.g., GPT-4o).")
    provider: str = Field(description="Provider name (e.g., OpenAI, Anthropic).")

class BenchmarkRunRequest(BaseModel):
    model_id: str = Field(description="ID of the selected model.")
    endpoint_id: str = Field(description="ID of the target endpoint.")
    prompt_text: str = Field(description="The prompt to be tested.")
    # Optional configuration parameters
    max_tokens: int = Field(default=1024, description="Maximum output tokens.")

class BenchmarkResult(BaseModel):
    run_id: str
    model_name: str
    endpoint_id: str
    latency_ms: float
    tokens_generated: int
    status: str = "completed"

# Response wrapper for API endpoints
class ApiResponse(BaseModel):
    message: str
    data: Optional[List[any]] = None
    status: str = "success"