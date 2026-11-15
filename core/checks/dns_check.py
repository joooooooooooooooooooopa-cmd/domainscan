"""P-021..P-040: DNS & Infrastructure check."""
import asyncio
import socket
import time
from typing import Optional
import dns.resolver
import dns.rdatatype
import httpx

from core.shared.http_client import get_client
from core.shared.constants import GENERIC_MX_PROVIDERS
from core.shared.validators import is_private_ip

CLOUDFLARE_NS_SUFFIXES = ['.ns.cloudflare.com.', '.ns.cloudflare.com']

# Configure resolver for macOS (no /etc/resolv.conf)
_resolver = dns.resolver.Resolver(configure=False)
_resolver.nameservers = ['8.8.8.8', '1.1.1.1']
_resolver.timeout = 5
_resolver.lifetime = 5


async def check_dns(domain: str) -> dict:
    result = {
        'ns_servers': [],
        'ns_count': 0,
        'cloudflare_ns_pair': None,
        'a_records': [],
        'aaaa_records': [],
        'has_ipv6': False,
        'mx_records': [],
        'mx_provider': None,
        'has_mx': False,
        'spf': None,
        'has_spf': False,
        'spf_strict': False,
        'dmarc': None,
        'has_dmarc': False,
        'dmarc_policy': None,
        'asn': None,
        'asn_org': None,
        'country': None,
        'city': None,
        'cdn_detected': None,
        'cloud_provider': None,
        'response_time_ms': None,
        'is_fast': False,
    }

    tasks = [
        _resolve(domain, 'NS'),
        _resolve(domain, 'A'),
        _resolve(domain, 'AAAA'),
        _resolve(domain, 'MX'),
        _resolve(domain, 'TXT'),
        _resolve(f'_dmarc.{domain}', 'TXT'),
    ]
    ns_r, a_r, aaaa_r, mx_r, txt_r, dmarc_r = await asyncio.gather(*tasks)

    result['ns_servers'] = ns_r
    result['ns_count'] = len(ns_r)
    result['a_records'] = a_r
    result['aaaa_records'] = aaaa_r
    result['has_ipv6'] = len(aaaa_r) > 0
    result['mx_records'] = mx_r
    result['has_mx'] = len(mx_r) > 0

    cf_ns = sorted([ns for ns in ns_r if any(ns.lower().endswith(s) for s in CLOUDFLARE_NS_SUFFIXES)])
    if len(cf_ns) >= 2:
        names = [n.split('.')[0] for n in cf_ns]
        result['cloudflare_ns_pair'] = '+'.join(names)

    for mx in mx_r:
        mx_l = mx.lower()
        for provider, patterns in GENERIC_MX_PROVIDERS.items():
            if any(p in mx_l for p in patterns):
                result['mx_provider'] = provider
                break
        if result['mx_provider']:
            break

    for txt in txt_r:
        if txt.startswith('v=spf1'):
            result['spf'] = txt
            result['has_spf'] = True
            result['spf_strict'] = '-all' in txt
            break

    for txt in dmarc_r:
        if txt.startswith('v=DMARC1'):
            result['dmarc'] = txt
            result['has_dmarc'] = True
            if 'p=reject' in txt:
                result['dmarc_policy'] = 'reject'
            elif 'p=quarantine' in txt:
                result['dmarc_policy'] = 'quarantine'
            elif 'p=none' in txt:
                result['dmarc_policy'] = 'none'
            break

    # Filter out private IPs (SSRF protection)
    a_r = [ip for ip in a_r if not is_private_ip(ip)]
    result['a_records'] = a_r

    if a_r:
        ip = a_r[0]
        ip_info = await _get_ip_info(ip)
        result['asn'] = ip_info.get('asn')
        result['asn_org'] = ip_info.get('org')
        result['country'] = ip_info.get('country')
        result['city'] = ip_info.get('city')

        org_lower = (ip_info.get('org') or '').lower()
        if 'cloudflare' in org_lower:
            result['cdn_detected'] = 'Cloudflare'
            result['cloud_provider'] = 'Cloudflare'
        elif 'amazon' in org_lower or 'aws' in org_lower:
            result['cloud_provider'] = 'AWS'
        elif 'google' in org_lower:
            result['cloud_provider'] = 'GCP'
        elif 'microsoft' in org_lower or 'azure' in org_lower:
            result['cloud_provider'] = 'Azure'
        elif 'hetzner' in org_lower:
            result['cloud_provider'] = 'Hetzner'
        elif 'digitalocean' in org_lower:
            result['cloud_provider'] = 'DigitalOcean'
        elif 'yandex' in org_lower:
            result['cloud_provider'] = 'Yandex Cloud'
        elif 'akamai' in org_lower:
            result['cdn_detected'] = 'Akamai'

        result['response_time_ms'] = await _measure_latency(domain)
        if result['response_time_ms'] and result['response_time_ms'] < 500:
            result['is_fast'] = True

    return result


async def _resolve(name: str, rdtype: str) -> list:
    loop = asyncio.get_event_loop()
    try:
        answers = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: _resolver.resolve(name, rdtype)),
            timeout=5.0
        )
        results = []
        for rdata in answers:
            txt = rdata.to_text().strip('"')
            results.append(txt)
        return results
    except Exception:
        return []


async def _get_ip_info(ip: str) -> dict:
    async with get_client(timeout=5.0) as client:
        try:
            resp = await client.get(f'https://ipinfo.io/{ip}/json')
            if resp.status_code == 200:
                data = resp.json()
                org = data.get('org', '')
                asn = org.split(' ')[0] if org else None
                return {
                    'asn': asn,
                    'org': org,
                    'country': data.get('country'),
                    'city': data.get('city'),
                }
        except Exception:
            pass
    return {}


async def _measure_latency(domain: str) -> Optional[int]:
    times = []
    async with get_client(timeout=5.0) as client:
        for _ in range(3):
            try:
                start = time.monotonic()
                await client.head(f'https://{domain}', follow_redirects=True)
                elapsed = (time.monotonic() - start) * 1000
                times.append(elapsed)
            except Exception:
                break
    return int(sum(times) / len(times)) if times else None
