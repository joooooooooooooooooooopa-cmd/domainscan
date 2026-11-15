"""P-078..P-092: Technology stack detection."""
import re
from typing import Optional
import httpx
from core.shared.http_client import get_client
from core.shared.constants import CMS_SIGNATURES, FRAMEWORK_SIGNATURES, PAYMENT_SIGNATURES, CHAT_SIGNATURES

try:
    import mmh3
    HAS_MMH3 = True
except ImportError:
    HAS_MMH3 = False


async def check_tech(domain: str, html: str, headers: dict) -> dict:
    result = {
        'cms': None,
        'frontend_framework': None,
        'google_analytics_ids': [],
        'yandex_metrica_ids': [],
        'facebook_pixel_ids': [],
        'adsense_publisher_id': None,
        'payment_integrations': [],
        'chat_widget': None,
        'favicon_hash': None,
        'languages': [],
    }

    html_lower = html.lower() if html else ''

    for cms, patterns in CMS_SIGNATURES.items():
        for p in patterns:
            if p.lower() in html_lower:
                result['cms'] = cms
                break
        if result['cms']:
            break

    for fw, patterns in FRAMEWORK_SIGNATURES.items():
        for p in patterns:
            if p.lower() in html_lower:
                result['frontend_framework'] = fw
                break
        if result['frontend_framework']:
            break

    ga_pattern = re.compile(r'(?:UA-\d{4,10}-\d{1,4}|G-[A-Z0-9]{8,12})')
    result['google_analytics_ids'] = list(set(ga_pattern.findall(html)))

    ym_pattern = re.compile(r'ym\((\d{5,12})')
    result['yandex_metrica_ids'] = list(set(ym_pattern.findall(html)))

    fb_pattern = re.compile(r"fbq\(['\"]init['\"],\s*['\"](\d+)['\"]")
    result['facebook_pixel_ids'] = list(set(fb_pattern.findall(html)))

    adsense_pattern = re.compile(r'pub-(\d{10,20})')
    adsense_match = adsense_pattern.search(html)
    if adsense_match:
        result['adsense_publisher_id'] = f'pub-{adsense_match.group(1)}'

    for provider, patterns in PAYMENT_SIGNATURES.items():
        for p in patterns:
            if p.lower() in html_lower:
                result['payment_integrations'].append(provider)
                break

    for widget, patterns in CHAT_SIGNATURES.items():
        for p in patterns:
            if p.lower() in html_lower:
                result['chat_widget'] = widget
                break
        if result['chat_widget']:
            break

    result['favicon_hash'] = await _get_favicon_hash(domain)

    try:
        from langdetect import detect_langs
        text = _extract_text(html)
        if len(text) > 100:
            langs = detect_langs(text)
            result['languages'] = [{'lang': str(l.lang), 'prob': round(l.prob, 2)} for l in langs[:3]]
    except Exception:
        pass

    return result


async def _get_favicon_hash(domain: str) -> Optional[str]:
    if not HAS_MMH3:
        return None
    async with get_client(timeout=5.0) as client:
        for path in ['/favicon.ico', '/apple-touch-icon.png']:
            try:
                resp = await client.get(f'https://{domain}{path}')
                if resp.status_code == 200 and len(resp.content) > 100:
                    h = mmh3.hash(resp.content)
                    return str(h)
            except Exception:
                continue
    return None


def _extract_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        for tag in soup(['script', 'style', 'noscript', 'meta', 'link']):
            tag.decompose()
        return soup.get_text(separator=' ', strip=True)[:5000]
    except Exception:
        return ''
