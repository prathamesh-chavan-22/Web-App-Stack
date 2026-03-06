import logging
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)


async def fetch_images_for_chapter(search_terms: list[str], max_images: int = 3) -> list[str]:
    """Fetch educational images using Unsplash Source (free, no API key needed)."""
    images: list[str] = []

    for term in search_terms:
        if len(images) >= max_images:
            break
        try:
            # Unsplash Source provides free images via direct URL
            # The URL redirects to a random relevant image
            query = quote_plus(term.strip())
            # Use different sizes/seeds to get different images
            seed = len(images)
            img_url = f"https://images.unsplash.com/photo-{seed}?w=800&q=80&auto=format&fit=crop"

            # Try Unsplash search API (no key needed for source URLs)
            search_url = f"https://source.unsplash.com/800x400/?{query}"

            # Verify the URL resolves (Unsplash source redirects to actual image)
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.head(search_url)
                if resp.status_code == 200:
                    # Use the final redirected URL (actual image)
                    final_url = str(resp.url)
                    if final_url and "images.unsplash.com" in final_url:
                        images.append(final_url)
                    else:
                        # Fallback: use the source URL directly (browser will follow redirect)
                        images.append(search_url)

        except Exception as e:
            logger.warning(f"Image fetch failed for term '{term}': {e}")

    # If Unsplash didn't work, generate placeholder images with relevant keywords
    if not images:
        for term in search_terms[:max_images]:
            query = quote_plus(term.strip())
            # Fallback to a placeholder service
            images.append(f"https://placehold.co/800x400/1a1a2e/e0e0e0?text={query}")

    return images[:max_images]
