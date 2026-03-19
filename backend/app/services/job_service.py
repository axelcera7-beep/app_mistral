"""Job search service: JSearch (primary) + Adzuna (fallback) and CV-to-job matching via embeddings."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

import httpx
import numpy as np

from app.config import get_settings
from app.schemas import JobOfferResult
from app.services.embedding_service import get_embeddings

logger = logging.getLogger(__name__)

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com/search"


# ---------------------------------------------------------------------------
# 1. JSearch (RapidAPI) — primary source
# ---------------------------------------------------------------------------
async def search_jsearch_jobs(
    keywords: str,
    location: str,
    results_per_page: int = 50,
    country: str = "fr",
) -> List[JobOfferResult]:
    """Fetch jobs from JSearch API (Google Jobs aggregator: LinkedIn, Indeed, Glassdoor…).

    Returns an empty list if the API key is missing or the call fails.
    """
    settings = get_settings()
    if not settings.jsearch_api_key:
        logger.warning("JSearch API key missing — skipping.")
        return []

    query = f"{keywords} {location}" if location else keywords
    params = {
        "query": query,
        "country": country,
        "num_pages": "1",
        "page": "1",
        "date_posted": "month",
    }
    headers = {
        "X-RapidAPI-Key": settings.jsearch_api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    logger.info("JSearch search: query=%s, country=%s", query, country)

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(JSEARCH_BASE_URL, params=params, headers=headers)
            logger.info("JSearch status: %d", response.status_code)
            response.raise_for_status()
            data = response.json()
        except Exception:
            logger.exception("Error calling JSearch API")
            return []

    raw_results = data.get("data", [])
    logger.info("JSearch returned %d results", len(raw_results))

    jobs: List[JobOfferResult] = []
    for item in raw_results[:results_per_page]:
        job_id = item.get("job_id", "")
        title = item.get("job_title", "")
        company = item.get("employer_name", "Inconnue")

        # Location: try multiple fields — JSearch is inconsistent for French offers
        job_city = item.get("job_city") or ""
        job_state = item.get("job_state") or ""
        job_country = item.get("job_country") or ""
        if job_city and job_state:
            job_location = f"{job_city}, {job_state}"
        elif job_city:
            job_location = job_city
        elif job_state:
            job_location = job_state
        elif job_country:
            job_location = job_country
        else:
            # Fallback: extract from nested job_location object or raw fields
            loc_obj = item.get("job_location") or {}
            if isinstance(loc_obj, dict):
                job_location = loc_obj.get("display_name", "") or loc_obj.get("city", "")
            else:
                job_location = str(loc_obj) if loc_obj else ""

        description = item.get("job_description", "")
        salary_min = item.get("job_min_salary")
        salary_max = item.get("job_max_salary")
        salary = None
        if salary_min and salary_max:
            salary = f"{salary_min}–{salary_max} {item.get('job_salary_currency', '€')}"
        elif salary_min:
            salary = f"À partir de {salary_min} {item.get('job_salary_currency', '€')}"
        redirect_url = item.get("job_apply_link") or item.get("job_google_link", "")

        # Date: try datetime string first, then epoch timestamp
        created = item.get("job_posted_at_datetime_utc", "")
        if not created and item.get("job_posted_at_timestamp"):
            try:
                ts = int(item["job_posted_at_timestamp"])
                created = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            except (ValueError, TypeError):
                created = ""

        if title and redirect_url:
            jobs.append(JobOfferResult(
                id=str(job_id),
                title=title,
                company=company,
                location=job_location or "Non précisé",
                description=description,
                salary=salary,
                redirect_url=redirect_url,
                created=created,
            ))

    return jobs


# ---------------------------------------------------------------------------
# 2. Adzuna — fallback source
# ---------------------------------------------------------------------------
async def search_adzuna_jobs(
    keywords: str,
    location: str,
    results_per_page: int = 50,
    country: str = "fr",
) -> List[JobOfferResult]:
    """Fetch jobs from the Adzuna API. Returns an empty list if credentials are missing."""
    settings = get_settings()
    if not settings.adzuna_app_id or not settings.adzuna_api_key:
        logger.warning("Adzuna credentials missing — returning empty results.")
        return []

    url = f"{ADZUNA_BASE_URL}/{country}/search/1"
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_api_key,
        "what": keywords,
        "results_per_page": results_per_page,
        "content-type": "application/json",
    }
    if location:
        params["where"] = location
    logger.info("Adzuna search: keywords=%s, location=%s", keywords, location)

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url, params=params)
            logger.info("Adzuna status: %d", response.status_code)
            response.raise_for_status()
            data = response.json()
        except Exception:
            logger.exception("Error calling Adzuna API")
            return []

    raw_results = data.get("results", [])
    logger.info("Adzuna returned %d results", len(raw_results))

    return [
        JobOfferResult(
            id=str(item.get("id", "")),
            title=item.get("title", ""),
            company=item.get("company", {}).get("display_name", "Inconnue"),
            location=item.get("location", {}).get("display_name", "Inconnue"),
            description=item.get("description", ""),
            salary=item.get("salary_range_display", "Non précisé"),
            redirect_url=item.get("redirect_url", ""),
            created=item.get("created", ""),
        )
        for item in raw_results
    ]


# ---------------------------------------------------------------------------
# 3. Unified search — JSearch first, Adzuna fallback, deduplicate
# ---------------------------------------------------------------------------
async def search_jobs_all(
    keywords: str,
    location: str,
) -> List[JobOfferResult]:
    """Search across all configured sources: JSearch (primary) then Adzuna (fallback).

    Results are deduplicated by normalised title + company.
    """
    all_jobs: List[JobOfferResult] = []

    # Primary: JSearch
    jsearch_results = await search_jsearch_jobs(keywords, location)
    all_jobs.extend(jsearch_results)
    logger.info("JSearch contributed %d results", len(jsearch_results))

    # Fallback: Adzuna (temporarily disabled)
    # adzuna_results = await search_adzuna_jobs(keywords, location)
    # all_jobs.extend(adzuna_results)
    # logger.info("Adzuna contributed %d results", len(adzuna_results))

    # Deduplicate by normalised (title, company) pair
    deduplicated = _deduplicate_jobs(all_jobs)
    logger.info("Total after dedup: %d (from %d raw)", len(deduplicated), len(all_jobs))

    return deduplicated


def _deduplicate_jobs(jobs: List[JobOfferResult]) -> List[JobOfferResult]:
    """Remove duplicate job offers based on normalised title + company."""
    seen: set[str] = set()
    unique: List[JobOfferResult] = []
    for job in jobs:
        key = f"{job.title.lower().strip()}|{job.company.lower().strip()}"
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


# ---------------------------------------------------------------------------
# 4. CV matching via embeddings (unchanged)
# ---------------------------------------------------------------------------
def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0.0
    arr1, arr2 = np.array(v1), np.array(v2)
    norm1, norm2 = np.linalg.norm(arr1), np.linalg.norm(arr2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(arr1, arr2) / (norm1 * norm2))


async def match_jobs_with_cv(cv_text: str, jobs: List[JobOfferResult]) -> List[JobOfferResult]:
    """Score and rank jobs based on CV similarity using Mistral Embeddings."""
    if not jobs or not cv_text:
        return jobs

    texts = [cv_text] + [job.description[:1000] for job in jobs]

    try:
        vectors = await get_embeddings(texts)
        if len(vectors) < 2:
            return jobs

        cv_vector = vectors[0]
        for i, job_vec in enumerate(vectors[1:]):
            score = _cosine_similarity(cv_vector, job_vec)
            jobs[i].match_score = max(0.0, min(100.0, round(score * 100, 1)))

        return sorted(jobs, key=lambda j: j.match_score or 0, reverse=True)

    except Exception:
        logger.exception("Error during job matching")
        return jobs
