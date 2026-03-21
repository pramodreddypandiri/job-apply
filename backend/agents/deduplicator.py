"""Deduplication agent — URL normalisation and role fingerprinting."""

import hashlib
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "source", "mc_cid", "mc_eid", "fbclid", "gclid",
    "gh_jid", "gh_src",  # Greenhouse tracking
}


def normalise_url(url: str) -> str:
    """Strip tracking params, resolve redirects, return canonical URL."""
    parsed = urlparse(url)
    # Remove tracking query params
    query_params = parse_qs(parsed.query)
    clean_params = {k: v for k, v in query_params.items() if k not in TRACKING_PARAMS}
    clean_query = urlencode(clean_params, doseq=True)
    clean = parsed._replace(query=clean_query, fragment="")
    return urlunparse(clean).rstrip("/")


def normalise_title(title: str) -> str:
    """Remove seniority prefix and normalise title."""
    title = title.lower().strip()
    prefixes = ["senior ", "sr ", "sr. ", "staff ", "principal ", "lead ", "junior ", "jr ", "jr. "]
    for prefix in prefixes:
        if title.startswith(prefix):
            title = title[len(prefix):]
            break
    return title.strip()


def build_fingerprint(company: str, title: str, location: str) -> str:
    """Build a stable identity hash for deduplication."""
    normalised_title = normalise_title(title)
    key = f"{company.lower().strip()}|{normalised_title}|{location.lower().strip()}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]
