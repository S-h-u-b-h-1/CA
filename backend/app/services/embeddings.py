import random
from abc import ABC, abstractmethod
from typing import List
from app.core.config import settings

class EmbeddingProvider(ABC):
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text string"""
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    def get_embedding(self, text: str) -> List[float]:
        # Return a deterministic-looking mock vector of size 1536
        # To make it look slightly distinct for different chunks, seed with text length/hash
        random.seed(hash(text))
        return [random.uniform(-1, 1) for _ in range(1536)]


def get_embedding_provider() -> EmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == "mock":
        return MockEmbeddingProvider()
    else:
        # Extend here for OpenAI, Gemini, or Cohere
        return MockEmbeddingProvider()
