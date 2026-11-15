"""P-001..P-020: Domain & Registration check via RDAP."""
import asyncio
from datetime import datetime, timezone
from typing import Optional
import httpx
import tldextract

from core.shared.constants import TLD_RISK, HIGH_RISK_REGISTRARS, LOW_RISK_REGISTRARS, PRIVACY_PROVIDERS
from core.shared.http_client import get_client

RDAP_SERVERS = {
    'com': 'https://rdap.verisign.com/com/v1/domain/',
    'net': 'https://rdap.verisign.com/net/v1/domain/',
    'org': 'https://rdap.org/domain/',
    'io': 'https://rdap.nic.io/domain/',
    'ru': 'https://rdap.tcinet.ru/domain/',
}
RDAP_FALLBACK = 'https://rdap.org/domain/'


async def check_domain(domain: str) -> dict:
    result = {
        'created_at': None,
        'expires_at': None,
        'updated_at': None,
        'registration_period_years': None,
        'age_days': None,
        'registrar_name': None,
        'registrar_iana_id': None,
        'registrar_risk': 'unknown',
        'registrant_name': None,
        'registrant_email': None,
        'registrant_org': None,
        'registrant_country': None,
        'whois_privacy': False,
        'tld': None,
        'tld_risk': 'low',
        'statuses': [],
        'dnssec_enabled': False,
    }

    ext = tldextract.extract(domain)
    tld = ext.suffix.split('.')[-1] if ext.suffix else ''
    result['tld'] = tld

    for risk_level, tlds in TLD_RISK.items():
        if tld in tlds:
            result['tld_risk'] = risk_level
            break

    rdap_data = await _fetch_rdap(domain, tld)
    if not rdap_data or not rdap_data.get('events'):
        # Fallback to whois command
        whois_data = await _whois_fallback(domain)
        if whois_data:
            result.update(whois_data)
        if not rdap_data:
            return result

    now = datetime.now(timezone.utc)

    for event in rdap_data.get('events', []):
        action = event.get('eventAction', '')
        date_str = event.get('eventDate', '')
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            continue

        if action == 'registration':
            result['created_at'] = dt.isoformat()
            result['age_days'] = (now - dt).days
        elif action == 'expiration':
            result['expires_at'] = dt.isoformat()
        elif action in ('last changed', 'last update of RDAP database'):
            if action == 'last changed':
                result['updated_at'] = dt.isoformat()

    if result['created_at'] and result['expires_at']:
        try:
            c = datetime.fromisoformat(result['created_at'])
            e = datetime.fromisoformat(result['expires_at'])
            result['registration_period_years'] = round((e - c).days / 365.25, 1)
        except (ValueError, TypeError):
            pass

    result['statuses'] = rdap_data.get('status', [])

    sec_dns = rdap_data.get('secureDNS', {})
    result['dnssec_enabled'] = sec_dns.get('delegationSigned', False)

    for entity in rdap_data.get('entities', []):
        roles = entity.get('roles', [])
        vcard = _extract_vcard(entity)

        if 'registrar' in roles:
            result['registrar_name'] = vcard.get('fn', entity.get('handle', ''))
            pids = entity.get('publicIds', [])
            for pid in pids:
                if pid.get('type') == 'IANA Registrar ID':
                    result['registrar_iana_id'] = pid.get('identifier')

            reg_lower = (result['registrar_name'] or '').lower()
            if any(hr in reg_lower for hr in HIGH_RISK_REGISTRARS):
                result['registrar_risk'] = 'high'
            elif any(lr in reg_lower for lr in LOW_RISK_REGISTRARS):
                result['registrar_risk'] = 'low'
            else:
                result['registrar_risk'] = 'medium'

        if 'registrant' in roles:
            result['registrant_name'] = vcard.get('fn', '')
            result['registrant_email'] = vcard.get('email', '')
            result['registrant_org'] = vcard.get('org', '')
            result['registrant_country'] = vcard.get('country', '')

            name_lower = (result['registrant_name'] or '').lower()
            org_lower = (result['registrant_org'] or '').lower()
            combined = f"{name_lower} {org_lower}"
            if any(pp in combined for pp in PRIVACY_PROVIDERS):
                result['whois_privacy'] = True

    if not result['whois_privacy'] and result['registrant_name']:
        name_l = result['registrant_name'].lower()
        if any(pp in name_l for pp in PRIVACY_PROVIDERS):
            result['whois_privacy'] = True

    return result


async def _fetch_rdap(domain: str, tld: str) -> Optional[dict]:
    url = RDAP_SERVERS.get(tld, RDAP_FALLBACK) + domain
    async with get_client(timeout=8.0) as client:
        try:
            resp = await client.get(url, headers={'Accept': 'application/rdap+json'})
            if resp.status_code == 200:
                return resp.json()
        except (httpx.HTTPError, Exception):
            pass

        if tld in RDAP_SERVERS:
            try:
                resp = await client.get(RDAP_FALLBACK + domain, headers={'Accept': 'application/rdap+json'})
                if resp.status_code == 200:
                    return resp.json()
            except (httpx.HTTPError, Exception):
                pass
    return None


async def _whois_fallback(domain: str) -> Optional[dict]:
    """Parse system whois command output as fallback when RDAP fails."""
    import re
    # Validate domain to prevent command injection
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\.\-]+$', domain):
        return None
    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                'whois', '--', domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=12.0
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=12.0)
        text = stdout.decode('utf-8', errors='ignore')
    except Exception:
        return None

    if not text:
        return None

    # Extract the section relevant to our domain (skip IANA referral header)
    # Look for line containing our domain name after "domain" keyword
    domain_upper = domain.upper()
    lines = text.split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip().upper()
        # Match: "domain: example.com" or "Domain Name: example.com"
        if domain_upper in stripped and any(stripped.startswith(p) for p in ['DOMAIN:', 'DOMAIN NAME:']):
            start_idx = i
            break
    if start_idx > 0:
        text = '\n'.join(lines[start_idx:])

    result = {}
    now = datetime.now(timezone.utc)

    # Parse created date
    for pattern in [
        r'(?:created|Creation Date|Registration Date|registered|domain_dateregistered)[\s:]+(\d{4}[\-/.]\d{2}[\-/.]\d{2}(?:[T ]\S+)?)',
        r'created:\s+(\d{4}-\d{2}-\d{2}[T ]\S+)',
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            date_str = m.group(1).replace('/', '-').strip()
            try:
                if 'T' in date_str:
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(date_str[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                result['created_at'] = dt.isoformat()
                result['age_days'] = (now - dt).days
            except (ValueError, TypeError):
                pass
            break

    # Parse expiry date
    for pattern in [
        r'(?:paid-till|Expir(?:y|ation) Date|Registry Expiry Date|expires|free-date)[\s:]+(\d{4}[\-/.]\d{2}[\-/.]\d{2}(?:[T ]\S+)?)',
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            date_str = m.group(1).replace('/', '-').strip()
            try:
                if 'T' in date_str:
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(date_str[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                result['expires_at'] = dt.isoformat()
            except (ValueError, TypeError):
                pass
            break

    if result.get('created_at') and result.get('expires_at'):
        try:
            c = datetime.fromisoformat(result['created_at'])
            e = datetime.fromisoformat(result['expires_at'])
            result['registration_period_years'] = round((e - c).days / 365.25, 1)
        except (ValueError, TypeError):
            pass

    # Parse registrar (skip "Registrar WHOIS Server" lines)
    m = re.search(r'(?:^|\n)\s*(?:Registrar|Sponsoring Registrar)\s*:\s*(?!WHOIS)(.+)', text, re.IGNORECASE)
    if m:
        registrar = m.group(1).strip()
        result['registrar_name'] = registrar
        reg_lower = registrar.lower()
        if any(hr in reg_lower for hr in HIGH_RISK_REGISTRARS):
            result['registrar_risk'] = 'high'
        elif any(lr in reg_lower for lr in LOW_RISK_REGISTRARS):
            result['registrar_risk'] = 'low'
        else:
            result['registrar_risk'] = 'medium'

    # Parse org
    m = re.search(r'(?:org|Registrant Organization|Organisation)[\s:]+(.+)', text, re.IGNORECASE)
    if m:
        org = m.group(1).strip()
        if org and org.lower() not in ('', 'n/a', 'none', 'not disclosed'):
            result['registrant_org'] = org

    # Parse country
    m = re.search(r'(?:Registrant Country|country)[\s:]+(\S+)', text, re.IGNORECASE)
    if m:
        result['registrant_country'] = m.group(1).strip()

    # Detect privacy
    text_lower = text.lower()
    if any(pp in text_lower for pp in PRIVACY_PROVIDERS):
        result['whois_privacy'] = True

    return result if result else None


def _extract_vcard(entity: dict) -> dict:
    result = {}
    vcard_array = entity.get('vcardArray', [])
    if len(vcard_array) < 2:
        return result
    for item in vcard_array[1]:
        if not isinstance(item, list) or len(item) < 4:
            continue
        prop = item[0]
        value = item[3]
        if prop == 'fn':
            result['fn'] = value if isinstance(value, str) else str(value)
        elif prop == 'email':
            result['email'] = value if isinstance(value, str) else str(value)
        elif prop == 'org':
            result['org'] = value if isinstance(value, str) else (value[0] if isinstance(value, list) and value else str(value))
        elif prop == 'adr':
            if isinstance(value, list) and len(value) >= 7:
                result['country'] = value[6] if value[6] else ''
    return result
