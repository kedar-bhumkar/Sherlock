"""
Ollama service for local vision-enabled LLM inference.

This module provides integration with Ollama for running vision-enabled LLMs locally,
specifically supporting models like qwen3-vl:4b for image content extraction.

Configuration:
    Set the following environment variable in your .env file:
    - OLLAMA_BASE_URL: URL of the Ollama server (default: http://localhost:11434)

Usage Example:
    ```python
    from services.ollama_service import OllamaService

    # Initialize service with specific model
    ollama = OllamaService(model_name="qwen3-vl:4b")

    # Check if server is accessible
    if await ollama.check_health():
        # Generate content from image
        result = await ollama.generate_with_image(
            prompt="Extract all text from this image",
            image_bytes=image_data,
        )
    ```

Supported Models:
    - qwen3-vl:4b (recommended for vision tasks)
    - llava:7b
    - llava:13b
    - bakllava:latest
    - Any other vision-enabled model available in Ollama

Setup Instructions:
    1. Install Ollama: https://ollama.ai/
    2. Pull a vision model: `ollama pull qwen3-vl:4b`
    3. Verify model is available: `ollama list`
    4. Start Ollama server (usually runs automatically)
    5. Configure OLLAMA_BASE_URL in .env if not using default

LLM Configuration (Supabase Config Table):
    Add to the "llms" config key:
    ```json
    {
      "llms": {
        "local": [
          {
            "id": "qwen3-vl:4b",
            "name": "Qwen3 VL 4B",
            "provider": "ollama",
            "model": "qwen3-vl:4b",
            "default": true
          }
        ]
      }
    }
    ```
"""

import base64
import json
from typing import Optional

import httpx

from settings.config import get_settings
from utils.retry_utils import with_retry, RetryConfig
from exceptions.llm_exceptions import (
    LLMConnectionError,
    LLMResponseError,
    LLMConfigurationError,
)
from exceptions.ingestion_exceptions import ExtractionError


class OllamaService:
    """
    Service for interacting with Ollama local LLM inference server.

    Supports vision-enabled models like qwen3-vl for image content extraction.
    """

    def __init__(self, model_name: str = "qwen3-vl:4b"):
        """
        Initialize Ollama service.

        Args:
            model_name: Name of the Ollama model to use (default: qwen3-vl:4b)
        """
        self.model_name = model_name
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url

    def _validate_configuration(self) -> None:
        """
        Validate Ollama configuration.

        Raises:
            LLMConfigurationError: If configuration is invalid
        """
        if not self.base_url:
            raise LLMConfigurationError(
                self.model_name,
                "OLLAMA_BASE_URL not configured in environment"
            )

    @with_retry(
        config=RetryConfig(max_attempts=3),
        retryable_exceptions=(ExtractionError, LLMConnectionError),
    )
    async def generate_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        temperature: float = 0.1,
        timeout: float = 120.0,
    ) -> str:
        """
        Generate text from image using Ollama vision model.

        Args:
            prompt: Text prompt for the model
            image_bytes: Raw image bytes
            temperature: Model temperature (0.0-1.0, lower is more deterministic)
            timeout: Request timeout in seconds

        Returns:
            Generated text response

        Raises:
            LLMConnectionError: If cannot connect to Ollama server
            LLMResponseError: If response is invalid
            ExtractionError: If generation fails
        """
        self._validate_configuration()

        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Prepare request payload
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()

                data = response.json()
                response_text = data.get("response", "")

                if not response_text:
                    raise LLMResponseError(
                        "ollama",
                        f"Empty response from model {self.model_name}"
                    )

                return response_text

        except httpx.ConnectError as e:
            raise LLMConnectionError(
                "ollama",
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Ensure Ollama is running and accessible. Error: {e}"
            )
        except httpx.TimeoutException as e:
            raise ExtractionError(
                "",
                self.model_name,
                f"Request timed out after {timeout}s: {e}"
            )
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 404:
                raise LLMConfigurationError(
                    self.model_name,
                    f"Model '{self.model_name}' not found. "
                    f"Pull it with: ollama pull {self.model_name}"
                )
            elif status_code >= 500:
                raise ExtractionError(
                    "",
                    self.model_name,
                    f"Ollama server error (HTTP {status_code}): {e}"
                )
            else:
                raise LLMResponseError(
                    "ollama",
                    f"HTTP {status_code}: {e}"
                )
        except json.JSONDecodeError as e:
            raise LLMResponseError(
                "ollama",
                f"Invalid JSON response from Ollama: {e}"
            )
        except Exception as e:
            raise ExtractionError(
                "",
                self.model_name,
                f"Unexpected error during Ollama generation: {e}"
            )

    async def generate_chat_with_image(
        self,
        messages: list[dict],
        image_bytes: bytes,
        temperature: float = 0.1,
        timeout: float = 120.0,
    ) -> str:
        """
        Generate chat response with image using Ollama vision model.

        Alternative API using chat endpoint instead of generate.

        Args:
            messages: Chat messages in OpenAI format
            image_bytes: Raw image bytes
            temperature: Model temperature (0.0-1.0)
            timeout: Request timeout in seconds

        Returns:
            Generated text response

        Raises:
            LLMConnectionError: If cannot connect to Ollama server
            LLMResponseError: If response is invalid
            ExtractionError: If generation fails
        """
        self._validate_configuration()

        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Add image to the last user message
        for message in reversed(messages):
            if message.get("role") == "user":
                message["images"] = [image_b64]
                break

        # Prepare request payload
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()

                data = response.json()
                message = data.get("message", {})
                response_text = message.get("content", "")

                if not response_text:
                    raise LLMResponseError(
                        "ollama",
                        f"Empty response from model {self.model_name}"
                    )

                return response_text

        except httpx.ConnectError as e:
            raise LLMConnectionError(
                "ollama",
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Ensure Ollama is running and accessible. Error: {e}"
            )
        except httpx.TimeoutException as e:
            raise ExtractionError(
                "",
                self.model_name,
                f"Request timed out after {timeout}s: {e}"
            )
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 404:
                raise LLMConfigurationError(
                    self.model_name,
                    f"Model '{self.model_name}' not found. "
                    f"Pull it with: ollama pull {self.model_name}"
                )
            elif status_code >= 500:
                raise ExtractionError(
                    "",
                    self.model_name,
                    f"Ollama server error (HTTP {status_code}): {e}"
                )
            else:
                raise LLMResponseError(
                    "ollama",
                    f"HTTP {status_code}: {e}"
                )
        except json.JSONDecodeError as e:
            raise LLMResponseError(
                "ollama",
                f"Invalid JSON response from Ollama: {e}"
            )
        except Exception as e:
            raise ExtractionError(
                "",
                self.model_name,
                f"Unexpected error during Ollama chat: {e}"
            )

    async def check_health(self) -> bool:
        """
        Check if Ollama server is healthy and accessible.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """
        List available models in Ollama.

        Returns:
            List of model names

        Raises:
            LLMConnectionError: If cannot connect to Ollama server
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()

                data = response.json()
                models = data.get("models", [])
                return [model.get("name", "") for model in models if model.get("name")]

        except httpx.ConnectError as e:
            raise LLMConnectionError(
                "ollama",
                f"Cannot connect to Ollama at {self.base_url}: {e}"
            )
        except Exception as e:
            raise LLMConnectionError(
                "ollama",
                f"Failed to list models: {e}"
            )

    async def check_model_exists(self, model_name: Optional[str] = None) -> bool:
        """
        Check if a specific model exists in Ollama.

        Args:
            model_name: Model name to check (defaults to instance model_name)

        Returns:
            True if model exists, False otherwise
        """
        model_to_check = model_name or self.model_name
        try:
            models = await self.list_models()
            return model_to_check in models
        except Exception:
            return False
