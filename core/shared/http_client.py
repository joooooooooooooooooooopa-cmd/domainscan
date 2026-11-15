"""Shared async HTTP client."""
import httpx

USER_AGENT = "DomainScan/1.0 (+https://example.com/bot)"

def get_client(timeout: float = 10.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout, connect=5.0),
        follow_redirects=True,
        max_redirects=3,
        headers={"User-Agent": USER_AGENT},
        verify=True,
    )
