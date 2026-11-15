"""P-061..P-077: Legal transparency check."""
import re
from core.shared.constants import (
    COMPANY_PATTERNS, REG_NUMBER_PATTERNS, LICENSE_PATTERNS,
    JURISDICTION_KEYWORDS
)


async def check_legal(domain: str, html: str, legal_pages: dict) -> dict:
    result = {
        'tos_exists': 'tos' in legal_pages,
        'privacy_exists': 'privacy' in legal_pages,
        'aml_exists': 'aml' in legal_pages,
        'cookie_policy': 'cookies' in legal_pages,
        'refund_policy': 'refund' in legal_pages,
        'contacts_page': 'contacts' in legal_pages,
        'company_name': None,
        'registration_number': None,
        'jurisdiction': None,
        'license_number': None,
        'physical_address': None,
        'contact_email': None,
        'contact_phone': None,
        'social_links': {},
    }

    if not html:
        return result

    # Extract visible text only (strip scripts, styles, tags)
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html[:200_000], 'lxml')
        for tag in soup(['script', 'style', 'noscript', 'meta', 'link', 'svg', 'path']):
            tag.decompose()
        text = soup.get_text(separator=' ', strip=True)
    except Exception:
        # Fallback: crude tag removal
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', html[:200_000], flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)

    text_lower = text.lower()

    # Company name: require minimum context (word before/after the legal suffix)
    company_patterns_strict = [
        r'(?:[\w\-]{2,})\s+(?:LLC|Ltd\.?|Inc\.?|Corp\.?|GmbH|PLC|LLP)',
        r'(?:LLC|Ltd\.?|Inc\.?|Corp\.?|GmbH|PLC|LLP)\s+["\']?(?:[\w\-]{2,})',
        r'(?:ООО|ОАО|ЗАО|ПАО|АО)\s*[«"\'][\w\s\-]{2,}[»"\']',
        r'(?:ООО|ОАО|ЗАО|ПАО|АО)\s+[\w\-]{3,}',
        r'ИП\s+[А-ЯЁ][\w\s]{5,}',
    ]
    for pattern in company_patterns_strict:
        match = re.search(pattern, text)
        if match:
            name = match.group(0).strip()
            # Filter noise: too short, or common false positives
            if len(name) >= 5 and name.lower() not in ('inc', 'ltd', 'llc', 'corp', 'sa', 'gmbh'):
                result['company_name'] = name
                break

    for pattern in REG_NUMBER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['registration_number'] = match.group(0).strip()
            break

    for pattern in LICENSE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['license_number'] = match.group(0).strip()
            break

    # Jurisdiction: only match if near legal/company context words
    jurisdiction_context = ['registered', 'incorporated', 'license', 'jurisdiction', 'company',
                           'зарегистрирован', 'юрисдикция', 'лицензи', 'регистрац']
    has_legal_context = any(ctx in text_lower for ctx in jurisdiction_context)

    for jurisdiction, keywords in JURISDICTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                # Only assign if there's legal context OR it's a well-known offshore
                if has_legal_context or jurisdiction in ('Curacao', 'BVI', 'Seychelles', 'Anjouan', 'Belize'):
                    # Extra check: make sure keyword isn't just in a random sentence
                    idx = text_lower.find(kw)
                    surrounding = text_lower[max(0, idx-100):idx+100]
                    if any(ctx in surrounding for ctx in jurisdiction_context) or jurisdiction in ('Curacao', 'BVI', 'Seychelles'):
                        result['jurisdiction'] = jurisdiction
                        break
        if result['jurisdiction']:
            break

    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,10}')
    emails = email_pattern.findall(text)
    noise = ['example.com', 'sentry.io', 'wixpress', 'googleapis', '.png', '.jpg', '.svg', '.css', '.js', 'webpack', 'schema.org', 'w3.org', 'json', 'xml']
    filtered = [e for e in emails if len(e) <= 100 and not any(x in e.lower() for x in noise)]
    if filtered:
        result['contact_email'] = filtered[0]

    phone_pattern = re.compile(r'(?:\+\d{1,3}[\s\-]?)?\(?\d{3,5}\)?[\s\-]?\d{2,4}[\s\-]?\d{2,4}(?:[\s\-]?\d{2,4})?')
    phones = phone_pattern.findall(text)
    real_phones = []
    for p in phones:
        digits = re.sub(r'\D', '', p)
        # Valid phone: 7-15 digits, starts with reasonable prefix
        if 7 <= len(digits) <= 15 and not digits.startswith('2026') and not digits.startswith('2025') and not digits.startswith('2024'):
            real_phones.append(p.strip())
    if real_phones:
        result['contact_phone'] = real_phones[0]

    social_map = {
        'telegram': [r'(?:t\.me|telegram\.me)/[\w\-]+'],
        'vk': [r'vk\.com/[\w\-]+'],
        'instagram': [r'instagram\.com/[\w\-.]+'],
        'twitter': [r'(?:twitter\.com|x\.com)/[\w\-]+'],
        'youtube': [r'youtube\.com/(?:channel|c|@)[\w\-]+'],
        'facebook': [r'facebook\.com/[\w\-.]+'],
        'linkedin': [r'linkedin\.com/(?:company|in)/[\w\-]+'],
        'discord': [r'discord\.(?:gg|com/invite)/[\w\-]+'],
    }
    for platform, patterns in social_map.items():
        for p in patterns:
            match = re.search(p, text_lower)
            if match:
                result['social_links'][platform] = match.group(0)
                break

    return result
