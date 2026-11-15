"""P-041..P-049: SSL/TLS & Certificate check."""
import asyncio
import ssl
import socket
from datetime import datetime, timezone
from typing import Optional
import httpx
from core.shared.http_client import get_client


async def check_ssl(domain: str) -> dict:
    result = {
        'has_ssl': False,
        'issuer': None,
        'issuer_org': None,
        'valid_from': None,
        'valid_to': None,
        'expired': False,
        'self_signed': False,
        'cert_type': 'unknown',
        'san': [],
        'tls_versions': [],
        'cert_history_count': 0,
        'subdomains_from_ct': [],
    }

    # Run cert fetch, TLS version, and crt.sh all in parallel
    cert_task = asyncio.create_task(_get_certificate(domain))
    tls_task = asyncio.create_task(_check_tls_versions(domain))
    ct_task = asyncio.create_task(_fetch_crt_sh(domain))

    # Get cert first (most important)
    cert = await cert_task
    if not cert:
        # Cancel TLS task, still try crt.sh
        tls_task.cancel()
        try:
            ct_data = await asyncio.wait_for(ct_task, timeout=10.0)
            result['cert_history_count'] = ct_data.get('count', 0)
            result['subdomains_from_ct'] = ct_data.get('subdomains', [])
        except Exception:
            ct_task.cancel()
        return result

    result['has_ssl'] = True

    issuer_dict = dict(x[0] for x in cert.get('issuer', []) if x)
    result['issuer'] = issuer_dict.get('commonName', '')
    result['issuer_org'] = issuer_dict.get('organizationName', '')

    subject_dict = dict(x[0] for x in cert.get('subject', []) if x)

    not_before = cert.get('notBefore', '')
    not_after = cert.get('notAfter', '')
    try:
        vf = datetime.strptime(not_before, '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
        vt = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
        result['valid_from'] = vf.isoformat()
        result['valid_to'] = vt.isoformat()
        result['expired'] = vt < datetime.now(timezone.utc)
    except (ValueError, TypeError):
        pass

    # Self-signed: issuer and subject are IDENTICAL (full DN, not just org)
    if cert.get('issuer') == cert.get('subject'):
        result['self_signed'] = True

    san_entries = []
    for san_type, san_value in cert.get('subjectAltName', []):
        if san_type == 'DNS':
            san_entries.append(san_value)
    result['san'] = san_entries

    if 'Extended Validation' in str(cert.get('subject', '')) or 'EV ' in (result['issuer'] or ''):
        result['cert_type'] = 'EV'
    elif subject_dict.get('organizationName'):
        result['cert_type'] = 'OV'
    else:
        result['cert_type'] = 'DV'

    # Collect parallel results
    try:
        tls_versions = await asyncio.wait_for(tls_task, timeout=10.0)
        result['tls_versions'] = tls_versions
    except Exception:
        pass

    try:
        ct_data = await asyncio.wait_for(ct_task, timeout=15.0)
        result['cert_history_count'] = ct_data.get('count', 0)
        result['subdomains_from_ct'] = ct_data.get('subdomains', [])
    except Exception:
        pass

    return result


async def _get_certificate(domain: str) -> Optional[dict]:
    loop = asyncio.get_event_loop()
    try:
        def _fetch():
            ctx = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=8) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    return ssock.getpeercert()
        return await asyncio.wait_for(loop.run_in_executor(None, _fetch), timeout=12.0)
    except Exception as e:
        # Try with www. prefix
        try:
            def _fetch_www():
                ctx = ssl.create_default_context()
                with socket.create_connection((f'www.{domain}', 443), timeout=8) as sock:
                    with ctx.wrap_socket(sock, server_hostname=f'www.{domain}') as ssock:
                        return ssock.getpeercert()
            return await asyncio.wait_for(loop.run_in_executor(None, _fetch_www), timeout=12.0)
        except Exception:
            return None


async def _check_tls_versions(domain: str) -> list:
    versions = []
    loop = asyncio.get_event_loop()

    try:
        def _test():
            ctx = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    ver = ssock.version()
                    return ver
        ver = await asyncio.wait_for(loop.run_in_executor(None, _test), timeout=8.0)
        if ver:
            versions.append(ver)
    except Exception:
        pass

    return versions


async def _fetch_crt_sh(domain: str) -> dict:
    result = {'count': 0, 'subdomains': []}
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(25.0, connect=10.0),
                follow_redirects=True,
                headers={"User-Agent": "DomainScan/1.0"},
            ) as client:
                resp = await client.get(
                    f'https://crt.sh/?q=%.{domain}&output=json',
                    headers={'Accept': 'application/json'},
                )
                if resp.status_code == 200:
                    text = resp.text.strip()
                    if not text or text.startswith('<'):
                        break
                    data = resp.json()
                    if isinstance(data, list):
                        result['count'] = len(data)
                        subs = set()
                        for entry in data:
                            name_value = entry.get('name_value', '')
                            for line in name_value.split('\n'):
                                line = line.strip().lower()
                                if line and '*' not in line and line != domain:
                                    subs.add(line)
                        result['subdomains'] = sorted(subs)[:50]
                    return result
                break
        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            break
        except Exception:
            break
    return result
