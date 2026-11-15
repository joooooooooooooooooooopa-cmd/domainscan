"""Input validation and SSRF protection."""
import re
import ipaddress
import tldextract

PRIVATE_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('0.0.0.0/8'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
]

BLOCKED_TLDS = {'onion', 'local', 'internal', 'localhost'}
MAX_DOMAIN_LENGTH = 253
DOMAIN_REGEX = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$')


def normalize_and_validate(raw: str) -> str:
    raw = raw.strip().lower()
    for prefix in ['https://', 'http://', 'www.']:
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
    raw = raw.split('/')[0].split('?')[0].split('#')[0].split(':')[0]

    ext = tldextract.extract(raw)
    if not ext.domain or not ext.suffix:
        raise ValueError(f"Invalid domain: {raw}")

    domain = f"{ext.domain}.{ext.suffix}"

    if len(domain) > MAX_DOMAIN_LENGTH:
        raise ValueError(f"Domain too long: {len(domain)}")

    tld = ext.suffix.split('.')[-1]
    if tld in BLOCKED_TLDS:
        raise ValueError(f"Blocked TLD: .{tld}")

    if not DOMAIN_REGEX.match(domain):
        # Allow IDN domains (punycode)
        try:
            domain.encode('idna')
        except (UnicodeError, UnicodeDecodeError):
            raise ValueError(f"Invalid domain format: {domain}")

    # Block IP addresses as input
    try:
        ipaddress.ip_address(raw.split('.')[0] if '.' in raw else raw)
        raise ValueError("IP addresses not allowed, use domain name")
    except ValueError as e:
        if "IP addresses not allowed" in str(e):
            raise
        pass  # Not an IP, good

    return domain


def is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in net for net in PRIVATE_NETWORKS)
    except ValueError:
        return False
