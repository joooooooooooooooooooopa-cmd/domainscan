"""Main scan pipeline - orchestrates all checks."""
import asyncio
import time

from core.shared.validators import normalize_and_validate
from core.checks.domain_check import check_domain
from core.checks.dns_check import check_dns
from core.checks.ssl_check import check_ssl
from core.checks.security_check import check_security
from core.checks.content_check import check_content
from core.checks.tech_check import check_tech
from core.checks.legal_check import check_legal
from core.checks.reputation_check import check_reputation
from core.scoring.trust_score import compute_trust_score


async def run_scan(domain: str) -> dict:
    domain = normalize_and_validate(domain)
    start = time.monotonic()

    # Phase 1: Parallel independent checks
    tasks = {
        'domain_check': asyncio.create_task(check_domain(domain)),
        'dns_check': asyncio.create_task(check_dns(domain)),
        'ssl_check': asyncio.create_task(check_ssl(domain)),
        'security_check': asyncio.create_task(check_security(domain)),
        'content_check': asyncio.create_task(check_content(domain)),
        'reputation_check': asyncio.create_task(check_reputation(domain)),
    }

    scan_data = {}
    for name, task in tasks.items():
        try:
            scan_data[name] = await asyncio.wait_for(asyncio.shield(task), timeout=30.0)
        except asyncio.TimeoutError:
            task.cancel()
            scan_data[name] = {'error': 'timeout'}
        except Exception as e:
            scan_data[name] = {'error': str(e)}

    # Phase 2: Dependent checks (need HTML from content_check)
    content_data = scan_data.get('content_check', {})
    html = content_data.get('html', '')
    headers = content_data.get('headers', {})
    legal_pages = content_data.get('legal_pages', {})

    phase2_tasks = {
        'tech_check': asyncio.create_task(check_tech(domain, html, headers)),
        'legal_check': asyncio.create_task(check_legal(domain, html, legal_pages)),
    }

    for name, task in phase2_tasks.items():
        try:
            scan_data[name] = await asyncio.wait_for(asyncio.shield(task), timeout=15.0)
        except asyncio.TimeoutError:
            task.cancel()
            scan_data[name] = {'error': 'timeout'}
        except Exception as e:
            scan_data[name] = {'error': str(e)}

    # Phase 3: Scoring
    trust_score = compute_trust_score(scan_data)

    duration_ms = int((time.monotonic() - start) * 1000)

    return {
        'domain': domain,
        'trust_score': trust_score,
        'checks': scan_data,
        'duration_ms': duration_ms,
    }
