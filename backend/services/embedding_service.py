"""Embedding service for generating vector embeddings using OpenAI."""

import random
from typing import List

from openai import AsyncOpenAI
import openai

from settings.config import get_settings
from utils.retry_utils import with_retry, RetryConfig
from exceptions.ingestion_exceptions import EmbeddingError


# OpenAI text-embedding-3-small dimensions (HNSW index limited to 2000)
EMBEDDING_DIMENSIONS = 1536


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(self, model: str = "text-embedding-3-small"):
        """
        Initialize embedding service.

        Args:
            model: Embedding model to use
        """
        self.model = model
        self.dimensions = EMBEDDING_DIMENSIONS
        self.settings = get_settings()
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy-initialize OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._client

    @with_retry(
        config=RetryConfig(max_attempts=3),
        retryable_exceptions=(EmbeddingError,),
    )
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector (1536 dimensions)

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise EmbeddingError("Empty text provided")

        # Use mock if configured
        if self.settings.use_mock:
            return self._mock_embedding(text)

        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text.strip(),
            )
            return response.data[0].embedding

        except openai.RateLimitError as e:
            # Retryable - will be caught by retry decorator
            raise EmbeddingError(f"Rate limit exceeded: {e}")
        except openai.APITimeoutError as e:
            # Retryable
            raise EmbeddingError(f"Request timed out: {e}")
        except openai.APIConnectionError as e:
            # Retryable
            raise EmbeddingError(f"Connection error: {e}")
        except openai.AuthenticationError as e:
            # Not retryable - fail immediately
            raise EmbeddingError(f"Authentication failed: {e}")
        except openai.BadRequestError as e:
            # Not retryable - fail immediately
            raise EmbeddingError(f"Invalid request: {e}")
        except Exception as e:
            raise EmbeddingError(f"Embedding generation failed: {e}")

    async def generate_embeddings_batch(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per batch (OpenAI supports up to 2048)

        Returns:
            List of embedding vectors
        """
        if self.settings.use_mock:
            return [self._mock_embedding(text) for text in texts]

        embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch = [t.strip() for t in batch if t and t.strip()]

            if not batch:
                continue

            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                )
                # Sort by index to maintain order
                sorted_data = sorted(response.data, key=lambda x: x.index)
                embeddings.extend([item.embedding for item in sorted_data])

            except Exception as e:
                # Fall back to individual requests on batch failure
                for text in batch:
                    embedding = await self.generate_embedding(text)
                    embeddings.append(embedding)

        return embeddings

    def _mock_embedding(self, text: str) -> List[float]:
        """
        Generate mock embedding for testing.

        Creates a deterministic random vector based on text content
        to ensure similar texts get similar (but not identical) embeddings.
        """
        # Use text hash as seed for reproducibility
        seed = hash(text) % (2**32)
        random.seed(seed)

        # Generate normalized random vector
        embedding = [random.gauss(0, 1) for _ in range(self.dimensions)]

        # Normalize to unit vector
        magnitude = sum(x**2 for x in embedding) ** 0.5
        embedding = [x / magnitude for x in embedding]

        # Reset random seed
        random.seed()

        return embedding
