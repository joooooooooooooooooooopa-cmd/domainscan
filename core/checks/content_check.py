"""Content check - HTTP crawl, HTML fetch, legal page discovery."""
import asyncio
import re
from urllib.parse import urlparse
import httpx
from core.shared.constants import LEGAL_PATHS

LEGAL_KEYWORDS = {
    'tos': ['terms', 'условия', 'пользовательское соглашение', 'terms of service', 'terms of use', 'user agreement', 'оферта', 'agreement', 'legal/terms'],
    'privacy': ['privacy', 'конфиденциальност', 'персональн', 'privacy policy', 'data protection', 'обработк', 'legal/privacy'],
    'cookies': ['cookie', 'куки'],
    'refund': ['refund', 'return', 'возврат'],
    'contacts': ['contact', 'контакт', 'связаться', 'about us', 'о компании', 'о нас'],
}

# Browser-like UA to avoid blocks
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


def _make_client(timeout: float = 15.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout, connect=8.0),
        follow_redirects=True,
        max_redirects=5,
        headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*", "Accept-Language": "en-US,en;q=0.9,ru;q=0.8"},
        verify=True,
    )


async def check_content(domain: str) -> dict:
    result = {
        'html': '',
        'headers': {},
        'status_code': None,
        'redirect_chain': [],
        'final_url': None,
        'legal_pages': {},
        'error': None,
    }

    async with _make_client() as client:
        # Try multiple URL variants
        urls_to_try = [
            f'https://{domain}',
            f'https://www.{domain}',
            f'http://{domain}',
        ]
        resp = None
        for url in urls_to_try:
            try:
                resp = await client.get(url)
                if resp.status_code == 200 and len(resp.text) > 500:
                    break
                # Accept non-200 but with content
                if len(resp.text) > 500:
                    break
            except Exception:
                continue

        if resp is None:
            result['error'] = 'All URL variants failed'
            return result

        result['html'] = resp.text[:500_000]
        result['headers'] = dict(resp.headers)
        result['status_code'] = resp.status_code
        result['final_url'] = str(resp.url)
        result['redirect_chain'] = [str(r.url) for r in resp.history]

        # If HTML is very small, try www variant
        if len(result['html']) < 1000 and not domain.startswith('www.'):
            try:
                resp2 = await client.get(f'https://www.{domain}')
                if len(resp2.text) > len(result['html']):
                    result['html'] = resp2.text[:500_000]
                    result['headers'] = dict(resp2.headers)
                    result['status_code'] = resp2.status_code
                    result['final_url'] = str(resp2.url)
            except Exception:
                pass

        final_host = urlparse(result['final_url']).netloc if result['final_url'] else domain
        html = result['html']
        html_lower = html.lower()

        legal_found = {}

        # Method 1: Search all <a> tags for legal-related href or text
        link_pattern = re.compile(r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
        all_links = link_pattern.findall(html)

        for href, anchor_text in all_links:
            href_lower = href.lower()
            text_lower = anchor_text.lower().strip()
            text_clean = re.sub(r'<[^>]+>', '', text_lower).strip()

            for category, keywords in LEGAL_KEYWORDS.items():
                if category in legal_found:
                    continue
                for kw in keywords:
                    if kw in href_lower or kw in text_clean:
                        legal_found[category] = href
                        break

        # Method 1.5: Search all href attributes for legal-related URLs
        all_hrefs = re.findall(r'href=["\']([^"\']{5,200})["\']', html_lower)
        for href in all_hrefs:
            for category, keywords in LEGAL_KEYWORDS.items():
                if category in legal_found:
                    continue
                for kw in keywords:
                    if kw in href:
                        legal_found[category] = href
                        break

        # Method 2: Check known paths via HTTP on final host
        tasks = []
        for category, paths in LEGAL_PATHS.items():
            if category not in legal_found:
                for path in paths[:3]:
                    tasks.append(_check_page(client, final_host, path, category))

        if tasks:
            page_results = await asyncio.gather(*tasks)
            for cat, path, exists in page_results:
                if exists and cat not in legal_found:
                    legal_found[cat] = path

        # Method 3: Check common subdomains
        if len(legal_found) < 2:
            policy_hosts = [f'policies.{domain}', f'legal.{domain}', f'www.{domain}']
            for phost in policy_hosts:
                if phost == final_host:
                    continue
                try:
                    r = await client.get(f'https://{phost}/', follow_redirects=True)
                    if r.status_code == 200 and len(r.text) > 500:
                        r_lower = r.text.lower()
                        if 'tos' not in legal_found and any(kw in r_lower for kw in ['terms', 'условия']):
                            legal_found['tos'] = f'https://{phost}/'
                        if 'privacy' not in legal_found and any(kw in r_lower for kw in ['privacy', 'конфиденциальност']):
                            legal_found['privacy'] = f'https://{phost}/'
                        if legal_found:
                            break
                except Exception:
                    continue

        result['legal_pages'] = legal_found

    return result


async def _check_page(client: httpx.AsyncClient, host: str, path: str, category: str) -> tuple:
    try:
        resp = await client.get(f'https://{host}{path}', follow_redirects=True)
        exists = resp.status_code == 200 and len(resp.text) > 200
        return (category, path, exists)
    except Exception:
        return (category, path, False)
