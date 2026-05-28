"""
Embedding utilities for semantic search and caching
"""
import hashlib
from typing import List, Optional
from app.services.llm_gateway import gateway


def compute_prompt_hash(prompt: str) -> str:
    """Compute SHA-256 hash of a prompt for caching."""
    return hashlib.sha256(prompt.encode()).hexdigest()


async def generate_embeddings(
    texts: List[str],
    model: str = "text-embedding-3-small",
    provider: str = "openai",
    api_key: Optional[str] = None
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.
    
    Args:
        texts: List of texts to embed
        model: Embedding model name
        provider: Provider to use
        api_key: Optional API key
        
    Returns:
        List of embedding vectors
    """
    return await gateway.embeddings(texts, model, provider, api_key)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Args:
        a: First vector
        b: Second vector
        
    Returns:
        Cosine similarity score (0-1)
    """
    if len(a) != len(b):
        raise ValueError("Vectors must have same length")
    
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)
