"""Service to interact with Mistral Embeddings API to calculate match scores."""

import hashlib
import logging

from mistralai import Mistral
from app.config import get_settings

logger = logging.getLogger(__name__)

# In-memory embedding cache: MD5(text) → vector
# Avoids redundant API calls when the same text (e.g. a CV) is used across searches.
_cache: dict[str, list[float]] = {}


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Get raw embedding vectors for a list of texts using mistral-embed.
    Results are cached in memory by text content to avoid redundant API calls.
    """
    if not texts:
        return []

    # Separate cached from uncached
    results: list[list[float] | None] = [None] * len(texts)
    uncached_indices: list[int] = []
    uncached_texts: list[str] = []

    for i, text in enumerate(texts):
        key = hashlib.md5(text.encode()).hexdigest()
        if key in _cache:
            results[i] = _cache[key]
        else:
            uncached_indices.append(i)
            uncached_texts.append(text)

    if uncached_texts:
        settings = get_settings()
        logger.info(
            "Calling mistral-embed API for %d inputs (%d served from cache)",
            len(uncached_texts),
            len(texts) - len(uncached_texts),
        )
        try:
            client = Mistral(api_key=settings.mistral_api_key)
            response = await client.embeddings.create_async(
                model=settings.embed_model,
                inputs=uncached_texts,
            )
            for idx, item in zip(uncached_indices, response.data):
                key = hashlib.md5(texts[idx].encode()).hexdigest()
                _cache[key] = item.embedding
                results[idx] = item.embedding
        except Exception:
            logger.exception("Error fetching embeddings via Mistral")
            return []

    return [r for r in results if r is not None]
