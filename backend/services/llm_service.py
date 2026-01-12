"""LLM service for vision-based content extraction using multiple providers."""

import json
import random
import base64
from dataclasses import dataclass

import google.generativeai as genai
from openai import AsyncOpenAI
import openai
from anthropic import AsyncAnthropic
import anthropic
from pydantic import ValidationError

from settings.config import get_settings
from utils.retry_utils import with_retry, RetryConfig
from utils.image_utils import get_mime_type
from exceptions.ingestion_exceptions import ExtractionError
from exceptions.llm_exceptions import LLMConfigurationError, LLMConnectionError
from services.ollama_service import OllamaService
from services.extraction_models import (
    ExtractionResponse,
    get_schema_example,
    get_json_schema,
)


@dataclass
class ExtractionResult:
    """Result from LLM vision extraction."""

    raw_data: str
    paraphrased_data: str
    title: str
    category: str
    subcategory: str
    topic: str
    is_new_category: bool = False
    is_new_subcategory: bool = False
    is_new_topic: bool = False


# Mock data for testing
MOCK_CATEGORIES = [
    ("Design", ["documentation", "architecture", "other"]),
    ("Code", ["frontend", "backend", "other"]),
    ("Domain", ["clinical", "non clinical", "other"]),
    ("Misc", ["roadmap", "strategy", "performance", "other"]),
]

MOCK_EXTRACTIONS = [
    {
        "raw_data": "This document outlines the system architecture for the healthcare platform. Key components include user authentication, patient records management, and real-time notifications.",
        "paraphrased_data": "The healthcare platform architecture comprises authentication, patient management, and notification systems working together to provide comprehensive healthcare services.",
        "title": "Healthcare Platform Architecture",
    },
    {
        "raw_data": "API endpoint specifications: GET /patients returns list of patients, POST /patients creates new patient record, PUT /patients/{id} updates patient information.",
        "paraphrased_data": "The API provides endpoints for listing, creating, and updating patient records through standard REST operations.",
        "title": "Patient API Endpoints",
    },
    {
        "raw_data": "Performance metrics dashboard showing response times, error rates, and throughput. Current P95 latency: 250ms, Error rate: 0.5%, Throughput: 1000 req/s.",
        "paraphrased_data": "System performance dashboard displays key metrics including 250ms P95 latency, 0.5% error rate, and 1000 requests per second throughput.",
        "title": "Performance Dashboard",
    },
    {
        "raw_data": "Clinical workflow diagram illustrating patient intake, diagnosis, treatment planning, and follow-up procedures. Includes decision points and approval gates.",
        "paraphrased_data": "Clinical workflow covers patient journey from intake through diagnosis, treatment, and follow-up with defined decision points.",
        "title": "Clinical Workflow Diagram",
    },
]


def _build_extraction_prompt(categories: list[dict] | None) -> str:
    """Build the extraction prompt with 3-level category hierarchy."""
    category_text = ""
    if categories:
        category_lines = []
        for cat in categories:
            cat_name = cat["name"]
            subcats = cat.get("subcategories", [])
            if subcats:
                for subcat in subcats:
                    subcat_name = subcat["name"] if isinstance(subcat, dict) else subcat
                    topics = subcat.get("topics", []) if isinstance(subcat, dict) else []
                    topics_str = ", ".join(topics) if topics else "other"
                    category_lines.append(f"  - {cat_name} > {subcat_name}: [{topics_str}]")
            else:
                category_lines.append(f"  - {cat_name}: (no subcategories yet)")
        category_text = "\n".join(category_lines)

    # Use the schema example from the Pydantic model
    schema_example = get_schema_example()

    return f"""Analyze this image and extract the following information. Return ONLY a valid JSON object with no additional text.

You MUST follow this EXACT JSON structure:

{schema_example}

## EXISTING CATEGORY HIERARCHY (Category > Subcategory: [topics]):
{category_text if category_text else "No existing categories defined yet. Create appropriate ones."}

## 3-LEVEL CLASSIFICATION RULES (FOLLOW IN STRICT ORDER):

1. **STRONGLY PREFER EXISTING HIERARCHY**: First, thoroughly evaluate if the content fits ANY existing category > subcategory > topic. Consider semantic similarity and conceptual overlap.

2. **HIERARCHY STRUCTURE**:
   - **Category**: Broad domain (Title Case): "Technology", "Healthcare", "Finance", "Marketing", "Legal", "Science", "Education"
   - **Subcategory**: Area within domain (lowercase): "frontend", "backend", "clinical", "patient care"
   - **Topic**: Specific subject (lowercase): "react components", "api design", "medical records", "workflows"

3. **SEMANTIC MATCHING**: Match by meaning, not just exact words:
   - Image of React code -> "Technology > frontend > react components"
   - Medical workflow diagram -> "Healthcare > clinical > workflows"
   - Database schema -> "Technology > backend > database design"

4. **AVOID "other" AT ALL COSTS**: The "other" topic is an ABSOLUTE LAST RESORT. Only use it if:
   - You've thoroughly considered ALL existing topics
   - The content truly doesn't fit anywhere AND
   - You cannot think of ANY meaningful new topic name
   - PREFER creating a NEW specific topic over using "other"

5. **CREATE NEW ENTRIES WHEN APPROPRIATE**: If content genuinely doesn't fit existing hierarchy:
   - Set "is_new": true for the level(s) you're creating
   - Make names descriptive but concise (2-4 words)
   - Topics should be the most specific - describe what the image is actually about

6. **EXAMPLES**:
   - Image of React component code:
     - If "Technology > frontend > react" exists: use it (all is_new: false)
     - If "Technology > frontend" exists but no react topic: add "react components" (topic.is_new: true)

   - Image of patient intake form:
     - If "Healthcare > clinical > patient intake" exists: use it
     - If only "Healthcare" exists: create "clinical > patient forms" (subcategory.is_new: true, topic.is_new: true)

   - Image of quarterly sales chart:
     - If no matching hierarchy exists: create "Finance > reports > quarterly sales" (all is_new: true)

## CRITICAL JSON STRUCTURE REQUIREMENTS:
- Return ONLY the JSON object, no markdown formatting or explanation
- The "paraphrased_data" field MUST be an object with "summary" (string) and "details" (array)
- Each item in "details" array MUST have "concept" (string) and "expanded_information" (string)
- The "category", "subcategory", and "topic" fields MUST be objects with "value" (string) and "is_new" (boolean)
- Ensure all text is properly escaped for JSON
- Be thorough in extracting raw_data - capture all visible text
- Category value must be Title Case, subcategory and topic values must be lowercase"""


def _parse_extraction_response(
    response_text: str,
    default_category: str = "Misc",
    default_subcategory: str = "general",
    default_topic: str = "general",
) -> ExtractionResult:
    """Parse LLM response into ExtractionResult with Pydantic validation."""
    try:
        # Try to extract JSON from response
        text = response_text.strip()

        # Handle markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (```json and ```)
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        data = json.loads(text)

        # Try to validate with Pydantic model first
        try:
            validated = ExtractionResponse.model_validate(data)

            # Normalize: category (Title Case), subcategory and topic (lowercase)
            category = validated.category.value.strip().title()
            subcategory = validated.subcategory.value.strip().lower()
            topic = validated.topic.value.strip().lower()

            return ExtractionResult(
                raw_data=validated.raw_data,
                paraphrased_data=validated.paraphrased_data.model_dump_json(),
                title=validated.title,
                category=category,
                subcategory=subcategory,
                topic=topic,
                is_new_category=validated.category.is_new,
                is_new_subcategory=validated.subcategory.is_new,
                is_new_topic=validated.topic.is_new,
            )
        except ValidationError:
            # Fall back to manual parsing if Pydantic validation fails
            pass

        # Manual parsing for backward compatibility with non-conforming responses
        paraphrased_data = data.get("paraphrased_data", "")
        if isinstance(paraphrased_data, (dict, list)):
            paraphrased_data = json.dumps(paraphrased_data)

        # Handle category - support both old (string) and new (object) formats
        category_data = data.get("category", default_category)
        if isinstance(category_data, dict):
            category = category_data.get("value", default_category)
            is_new_category = category_data.get("is_new", False)
        else:
            category = category_data
            is_new_category = False

        # Handle subcategory - support both old (string) and new (object) formats
        subcategory_data = data.get("subcategory", default_subcategory)
        if isinstance(subcategory_data, dict):
            subcategory = subcategory_data.get("value", default_subcategory)
            is_new_subcategory = subcategory_data.get("is_new", False)
        else:
            subcategory = subcategory_data
            is_new_subcategory = False

        # Handle topic - support both old (string) and new (object) formats
        topic_data = data.get("topic", default_topic)
        if isinstance(topic_data, dict):
            topic = topic_data.get("value", default_topic)
            is_new_topic = topic_data.get("is_new", False)
        else:
            topic = topic_data
            is_new_topic = False

        # Normalize: category (Title Case), subcategory and topic (lowercase)
        if category:
            category = category.strip().title()
        if subcategory:
            subcategory = subcategory.strip().lower()
        if topic:
            topic = topic.strip().lower()

        return ExtractionResult(
            raw_data=data.get("raw_data", ""),
            paraphrased_data=paraphrased_data,
            title=data.get("title", "Untitled"),
            category=category,
            subcategory=subcategory,
            topic=topic,
            is_new_category=is_new_category,
            is_new_subcategory=is_new_subcategory,
            is_new_topic=is_new_topic,
        )
    except json.JSONDecodeError:
        # If JSON parsing fails, try to extract what we can
        return ExtractionResult(
            raw_data=response_text,
            paraphrased_data="Failed to parse structured response",
            title="Extraction Result",
            category=default_category,
            subcategory=default_subcategory,
            topic=default_topic,
            is_new_category=False,
            is_new_subcategory=False,
            is_new_topic=False,
        )


class LLMService:
    """Service for extracting content from images using vision LLMs."""

    def __init__(self, llm_type: str = "web", llm_id: str = "gemini-3-flash-preview"):
        """
        Initialize LLM service.

        Args:
            llm_type: "web" or "local"
            llm_id: LLM identifier (e.g., "gemini-3-flash-preview", "claude-sonnet-4", "qwen3-vl:4b")
        """
        self.llm_type = llm_type
        self.llm_id = llm_id
        self.settings = get_settings()

        # Lazy-initialized clients
        self._openai_client: AsyncOpenAI | None = None
        self._anthropic_client: AsyncAnthropic | None = None
        self._ollama_service: OllamaService | None = None

    @property
    def openai_client(self) -> AsyncOpenAI:
        """Lazy-initialize OpenAI client."""
        if self._openai_client is None:
            if not self.settings.openai_api_key:
                raise LLMConfigurationError(self.llm_id, "OpenAI API key not configured")
            self._openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._openai_client

    @property
    def anthropic_client(self) -> AsyncAnthropic:
        """Lazy-initialize Anthropic client."""
        if self._anthropic_client is None:
            if not self.settings.anthropic_api_key:
                raise LLMConfigurationError(self.llm_id, "Anthropic API key not configured")
            self._anthropic_client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        return self._anthropic_client

    @property
    def ollama_service(self) -> OllamaService:
        """Lazy-initialize Ollama service."""
        if self._ollama_service is None:
            self._ollama_service = OllamaService(model_name=self.llm_id)
        return self._ollama_service

    @with_retry(
        config=RetryConfig(max_attempts=3),
        retryable_exceptions=(ExtractionError,),
    )
    async def extract_content(
        self,
        image_bytes: bytes,
        available_categories: list[dict] | None = None,
    ) -> ExtractionResult:
        """
        Extract content from image using vision LLM.

        Args:
            image_bytes: Raw image bytes
            available_categories: List of category dicts with subcategories and topics

        Returns:
            ExtractionResult with extracted and paraphrased content

        Raises:
            ExtractionError: If extraction fails
        """
        # Use mock if configured
        if self.settings.use_mock:
            return await self._mock_extract(image_bytes, available_categories)

        # Route to appropriate provider
        if self.llm_type == "local":
            return await self._extract_with_ollama(image_bytes, available_categories)
        elif self.llm_id.startswith("gpt"):
            return await self._extract_with_openai(image_bytes, available_categories)
        elif self.llm_id.startswith("claude"):
            return await self._extract_with_anthropic(image_bytes, available_categories)
        elif self.llm_id.startswith("gemini"):
            return await self._extract_with_google(image_bytes, available_categories)
        else:
            # Default to OpenAI
            return await self._extract_with_openai(image_bytes, available_categories)

    async def _extract_with_openai(
        self,
        image_bytes: bytes,
        available_categories: list[dict] | None = None,
    ) -> ExtractionResult:
        """Extract using OpenAI GPT-4o Vision."""
        prompt = _build_extraction_prompt(available_categories)

        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = get_mime_type(image_bytes) or "image/jpeg"

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.llm_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=4096,
            )

            response_text = response.choices[0].message.content
            return _parse_extraction_response(response_text)

        except openai.RateLimitError as e:
            raise ExtractionError("", self.llm_id, f"Rate limit exceeded: {e}")
        except openai.APITimeoutError as e:
            raise ExtractionError("", self.llm_id, f"Request timed out: {e}")
        except openai.APIConnectionError as e:
            raise ExtractionError("", self.llm_id, f"Connection error: {e}")
        except openai.AuthenticationError as e:
            raise LLMConfigurationError(self.llm_id, f"Authentication failed: {e}")
        except Exception as e:
            raise ExtractionError("", self.llm_id, str(e))

    async def _extract_with_anthropic(
        self,
        image_bytes: bytes,
        available_categories: list[dict] | None = None,
    ) -> ExtractionResult:
        """Extract using Anthropic Claude Vision."""
        prompt = _build_extraction_prompt(available_categories)

        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = get_mime_type(image_bytes) or "image/jpeg"

        try:
            response = await self.anthropic_client.messages.create(
                model=self.llm_id,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": image_b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )

            response_text = response.content[0].text
            return _parse_extraction_response(response_text)

        except anthropic.RateLimitError as e:
            raise ExtractionError("", self.llm_id, f"Rate limit exceeded: {e}")
        except anthropic.APITimeoutError as e:
            raise ExtractionError("", self.llm_id, f"Request timed out: {e}")
        except anthropic.APIConnectionError as e:
            raise ExtractionError("", self.llm_id, f"Connection error: {e}")
        except anthropic.AuthenticationError as e:
            raise LLMConfigurationError(self.llm_id, f"Authentication failed: {e}")
        except Exception as e:
            raise ExtractionError("", self.llm_id, str(e))

    async def _extract_with_ollama(
        self,
        image_bytes: bytes,
        available_categories: list[dict] | None = None,
    ) -> ExtractionResult:
        """
        Extract using Ollama local model (e.g., qwen3-vl:4b, llava).

        This method uses the dedicated OllamaService for better modularity
        and maintainability. Uses the /api/chat endpoint which works better
        with vision models like qwen3-vl.
        """
        prompt = _build_extraction_prompt(available_categories)

        # Build chat messages format for better compatibility with vision models
        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        try:
            # Use the chat endpoint which works better with qwen3-vl and other vision models
            response_text = await self.ollama_service.generate_chat_with_image(
                messages=messages,
                image_bytes=image_bytes,
                temperature=0.1,
                timeout=180.0,  # Longer timeout for vision processing
            )
            return _parse_extraction_response(response_text)

        except (LLMConnectionError, LLMConfigurationError):
            # Re-raise LLM-specific errors as-is
            raise
        except Exception as e:
            # Wrap other exceptions as ExtractionError
            raise ExtractionError("", self.llm_id, str(e))

    async def _extract_with_google(
        self,
        image_bytes: bytes,
        available_categories: list[dict] | None = None,
    ) -> ExtractionResult:
        """Extract using Google Gemini Vision."""
        prompt = _build_extraction_prompt(available_categories)
        mime_type = get_mime_type(image_bytes) or "image/jpeg"

        if not self.settings.google_api_key:
            raise LLMConfigurationError(self.llm_id, "Google API key not configured")

        try:
            genai.configure(api_key=self.settings.google_api_key)
            
            # Map common internal names to actual Gemini models if needed
            model_name = self.llm_id
            if "gemini-3" in model_name: # Handle future-proof or placeholder names
                model_name = "gemini-3-flash-preview"
            
            model = genai.GenerativeModel(model_name)
            
            response = await model.generate_content_async(
                [
                    prompt,
                    {
                        "mime_type": mime_type,
                        "data": image_bytes
                    }
                ],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                )
            )

            # Gemini might block content or return empty text if it violates safety filters
            try:
                response_text = response.text
            except ValueError:
                # If the response doesn't contain text (e.g. blocked)
                raise ExtractionError("", self.llm_id, "Gemini response was blocked or contains no text")

            if not response_text:
                raise ExtractionError("", self.llm_id, "Empty response from Gemini")

            return _parse_extraction_response(response_text)

        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                raise ExtractionError("", self.llm_id, f"Rate limit exceeded: {e}")
            raise ExtractionError("", self.llm_id, str(e))

    async def _mock_extract(
        self,
        image_bytes: bytes,
        available_categories: list[dict] | None = None,
    ) -> ExtractionResult:
        """Mock extraction for testing."""
        # Pick random mock extraction
        mock = random.choice(MOCK_EXTRACTIONS)

        # Generate random category hierarchy
        mock_categories = ["Design", "Code", "Domain", "Technology"]
        mock_subcategories = ["frontend", "backend", "architecture", "clinical"]
        mock_topics = ["components", "api design", "workflows", "documentation"]

        return ExtractionResult(
            raw_data=mock["raw_data"],
            paraphrased_data=mock["paraphrased_data"],
            title=mock["title"],
            category=random.choice(mock_categories),
            subcategory=random.choice(mock_subcategories),
            topic=random.choice(mock_topics),
            is_new_category=False,
            is_new_subcategory=False,
            is_new_topic=False,
        )
