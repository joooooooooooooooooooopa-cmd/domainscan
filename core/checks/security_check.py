"""Security check - blacklists, headers, redirects, robots, forms, cookies."""
import asyncio
import re
import dns.resolver
import httpx
from core.shared.constants import SECURITY_HEADERS

_resolver = dns.resolver.Resolver(configure=False)
_resolver.nameservers = ['8.8.8.8', '1.1.1.1']
_resolver.timeout = 5
_resolver.lifetime = 5

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"


async def check_security(domain: str) -> dict:
    result = {
        'spamhaus_dbl': False,
        'security_headers': {},
        'security_headers_count': 0,
        'security_headers_missing': [],
        'redirect_count': 0,
        'redirect_chain': [],
        'final_is_https': False,
        'mixed_content_risk': False,
        'has_robots_txt': False,
        'robots_disallow_all': False,
        'has_sitemap': False,
        'hsts_enabled': False,
        'hsts_max_age': 0,
        'hsts_preload': False,
        'hsts_include_subdomains': False,
        'has_login_form': False,
        'has_payment_form': False,
        'has_file_upload': False,
        'cookie_count': 0,
        'has_secure_cookies': False,
        'has_httponly_cookies': False,
        'meta_robots': None,
        'x_powered_by': None,
        'server_header': None,
    }

    spamhaus, page_info = await asyncio.gather(
        _check_spamhaus(domain),
        _check_page_security(domain),
    )

    result['spamhaus_dbl'] = spamhaus
    result.update(page_info)
    return result


async def _check_spamhaus(domain: str) -> bool:
    loop = asyncio.get_event_loop()
    try:
        lookup = f'{domain}.dbl.spamhaus.org'
        answers = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: _resolver.resolve(lookup, 'A')),
            timeout=5.0
        )
        for rdata in answers:
            if rdata.to_text().startswith('127.0.1.'):
                return True
        return False
    except Exception:
        return False


async def _check_page_security(domain: str) -> dict:
    info = {
        'security_headers': {},
        'security_headers_count': 0,
        'security_headers_missing': [],
    }

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(12.0, connect=5.0),
        follow_redirects=True,
        max_redirects=8,
        headers={"User-Agent": UA, "Accept": "text/html,*/*"},
    ) as client:
        resp = None
        for url in [f'https://www.{domain}', f'https://{domain}']:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    break
            except Exception:
                continue

        if resp is None:
            info['security_headers_missing'] = list(SECURITY_HEADERS)
            return info

        headers_lower = {k.lower(): v for k, v in resp.headers.items()}
        html = resp.text[:300_000].lower()

        # Security headers
        present = {}
        missing = []
        count = 0
        for h in SECURITY_HEADERS:
            if h in headers_lower:
                present[h] = headers_lower[h]
                count += 1
            else:
                missing.append(h)
        info['security_headers'] = present
        info['security_headers_count'] = count
        info['security_headers_missing'] = missing

        # Redirect chain
        info['redirect_count'] = len(resp.history)
        info['redirect_chain'] = [str(r.url) for r in resp.history][:5
        ]
        info['final_is_https'] = str(resp.url).startswith('https://')

        # HSTS analysis
        hsts = headers_lower.get('strict-transport-security', '')
        if hsts:
            info['hsts_enabled'] = True
            age_match = re.search(r'max-age=(\d+)', hsts)
            if age_match:
                info['hsts_max_age'] = int(age_match.group(1))
            info['hsts_preload'] = 'preload' in hsts
            info['hsts_include_subdomains'] = 'includesubdomains' in hsts.lower()

        # Server info
        info['x_powered_by'] = headers_lower.get('x-powered-by')
        info['server_header'] = headers_lower.get('server')

        # Cookie analysis
        cookies = resp.headers.get_list('set-cookie') if hasattr(resp.headers, 'get_list') else [v for k, v in resp.headers.multi_items() if k.lower() == 'set-cookie']
        info['cookie_count'] = len(cookies)
        if cookies:
            info['has_secure_cookies'] = any('secure' in c.lower() for c in cookies)
            info['has_httponly_cookies'] = any('httponly' in c.lower() for c in cookies)

        # Mixed content risk (http:// resources on https:// page)
        if str(resp.url).startswith('https://'):
            http_resources = re.findall(r'(?:src|href|action)=["\']http://', html)
            info['mixed_content_risk'] = len(http_resources) > 0

        # Meta robots
        meta_match = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)', html)
        if meta_match:
            info['meta_robots'] = meta_match.group(1)

        # Form detection
        forms = re.findall(r'<form[^>]*>(.*?)</form>', html, re.DOTALL)
        for form in forms:
            if re.search(r'type=["\']password["\']', form):
                info['has_login_form'] = True
            if re.search(r'(?:card.?number|cvv|cvc|expir|credit.?card)', form):
                info['has_payment_form'] = True
            if re.search(r'type=["\']file["\']', form):
                info['has_file_upload'] = True

        # Robots.txt & sitemap
        try:
            r = await client.get(f'https://{domain}/robots.txt')
            if r.status_code == 200 and 'user-agent' in r.text.lower():
                info['has_robots_txt'] = True
                if 'disallow: /' in r.text and 'disallow: / ' not in r.text:
                    lines = r.text.lower().split('\n')
                    for line in lines:
                        if line.strip() == 'disallow: /':
                            info['robots_disallow_all'] = True
                if 'sitemap:' in r.text.lower():
                    info['has_sitemap'] = True
        except Exception:
            pass

        if not info['has_sitemap']:
            try:
                r = await client.get(f'https://{domain}/sitemap.xml')
                if r.status_code == 200 and ('urlset' in r.text.lower() or 'sitemapindex' in r.text.lower()):
                    info['has_sitemap'] = True
            except Exception:
                pass

    return info
