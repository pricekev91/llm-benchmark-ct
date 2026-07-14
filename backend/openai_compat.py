import time
from typing import Dict, Any, List
import json

class LLMAdapter:
    """
    Abstract Base Class (Interface) for all LLM service adapters.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get("provider")
        print(f"Adapter initialized for provider: {self.provider}")

    def query(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """
        Executes the LLM query and returns detailed metrics.
        """
        raise NotImplementedError("Query method must be implemented by a subclass.")

class OpenAIAdapter(LLMAdapter):
    """Adapter for the official OpenAI API."""
    def query(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        # --- STUB: Real API call would go here using self.config['api_key'] ---
        start_time = time.time()
        
        # Simulate API response
        time.sleep(0.5) # Simulate network delay
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Simulated response data
        response_text = f"Simulated OpenAI response to prompt: {prompt[:30]}..."
        tokens_used = 512 # Simulated tokens
        output_length = len(response_text)
        
        return {
            "response_text": response_text,
            "latency_ms": latency_ms,
            "tokens_generated": tokens_used,
            "output_length": output_length,
        }

class LlamaCppAdapter(LLMAdapter):
    """Adapter for llama.cpp server endpoint."""
    def query(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        # --- STUB: Real interaction with localhost:8080/completion ---
        start_time = time.time()
        time.sleep(0.8)
        latency_ms = (time.time() - start_time) * 1000
        
        # Simulate response
        response_text = f"Simulated llama.cpp response: {prompt[:30]}..."
        tokens_used = 480 
        output_length = len(response_text)
        
        return {
            "response_text": response_text,
            "latency_ms": latency_ms,
            "tokens_generated": tokens_used,
            "output_length": output_length,
        }

class LiteLLMAdapter(LLMAdapter):
    """Adapter using the LiteLLM proxy for multi-backend abstraction."""
    def query(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        # --- STUB: Real interaction with LiteLLM proxy ---
        start_time = time.time()
        time.sleep(0.6)
        latency_ms = (time.time() - start_time) * 1000
        
        # Simulate response
        response_text = f"Simulated LiteLLM response: {prompt[:30]}..."
        tokens_used = 550
        output_length = len(response_text)
        
        return {
            "response_text": response_text,
            "latency_ms": latency_ms,
            "tokens_generated": tokens_used,
            "output_length": output_length,
        }

class LlamaSwapAdapter(LLMAdapter):
    """Adapter for Llama-Swap service."""
    def query(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        # --- STUB: Real interaction with Llama-Swap API ---
        start_time = time.time()
        time.sleep(0.7)
        latency_ms = (time.time() - start_time) * 1000
        
        # Simulate response
        response_text = f"Simulated Llama-Swap response: {prompt[:30]}..."
        tokens_used = 600
        output_length = len(response_text)
        
        return {
            "response_text": response_text,
            "latency_ms": latency_ms,
            "tokens_generated": tokens_used,
            "output_length": output_length,
        }

# Mapping of provider names to their respective adapter classes
ADAPTER_MAP = {
    "OpenAI": OpenAIAdapter,
    "llama.cpp": LlamaCppAdapter,
    "LiteLLM": LiteLLMAdapter,
    "llama-swap": LlamaSwapAdapter
}

def get_llm_adapter(model_config: Dict[str, Any]) -> LLMAdapter:
    """
    Factory function to instantiate the correct adapter based on the model configuration.
    """
    provider = model_config.get("provider")
    if provider not in ADAPTER_MAP:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    
    AdapterClass = ADAPTER_MAP[provider]
    return AdapterClass(model_config)