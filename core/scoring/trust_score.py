"""Trust Score computation: weighted categories + overrides."""


def clamp(value, lo=0, hi=100):
    return max(lo, min(hi, int(value)))


def compute_trust_score(scan_data: dict) -> dict:
    domain = scan_data.get('domain_check', {})
    dns_data = scan_data.get('dns_check', {})
    ssl_data = scan_data.get('ssl_check', {})
    security = scan_data.get('security_check', {})
    legal = scan_data.get('legal_check', {})
    tech = scan_data.get('tech_check', {})
    reputation = scan_data.get('reputation_check', {})

    scores = {}
    factors_positive = []
    factors_negative = []

    # --- Domain Score (weight 0.20) ---
    ds = 50
    age = domain.get('age_days')
    if age is not None:
        if age >= 1095:
            ds = 100
        elif age >= 365:
            ds = 75
        elif age >= 90:
            ds = 50
        elif age >= 30:
            ds = 25
        else:
            ds = 0
            factors_negative.append(f"Domain age: {age} days (very new)")

    if age and age >= 1095:
        factors_positive.append(f"Domain age: {age} days ({age // 365}+ years)")

    if domain.get('registrar_risk') == 'high':
        ds -= 20
        factors_negative.append(f"High-risk registrar: {domain.get('registrar_name', 'unknown')}")
    if domain.get('whois_privacy'):
        ds -= 15
        factors_negative.append("WHOIS privacy enabled (owner hidden)")
    if domain.get('tld_risk') == 'high':
        ds -= 10
        factors_negative.append(f"High-risk TLD: .{domain.get('tld', '?')}")

    reg_period = domain.get('registration_period_years')
    if reg_period is not None:
        if reg_period <= 1:
            ds -= 10
            factors_negative.append(f"Short registration: {reg_period} year(s)")
        elif reg_period >= 5:
            ds += 5
            factors_positive.append(f"Long registration: {reg_period} years")

    if domain.get('dnssec_enabled'):
        ds += 5
        factors_positive.append("DNSSEC enabled")

    scores['domain'] = clamp(ds)

    # --- Infrastructure Score (weight 0.12) ---
    infra = 50
    if dns_data.get('a_records'):
        infra += 8
    if dns_data.get('has_ipv6'):
        infra += 5
    if dns_data.get('has_mx'):
        infra += 8
        factors_positive.append(f"Has email (MX): {dns_data.get('mx_provider', 'custom')}")
    if dns_data.get('cdn_detected'):
        infra += 8
        factors_positive.append(f"CDN/WAF: {dns_data['cdn_detected']}")
    if dns_data.get('cloud_provider'):
        infra += 4
    if dns_data.get('has_spf'):
        infra += 5
        if dns_data.get('spf_strict'):
            infra += 3
    if dns_data.get('has_dmarc'):
        infra += 5
        if dns_data.get('dmarc_policy') == 'reject':
            infra += 3
            factors_positive.append("DMARC: reject policy")
    if dns_data.get('ns_count', 0) >= 2:
        infra += 3
    if dns_data.get('is_fast'):
        infra += 3

    latency = dns_data.get('response_time_ms')
    if latency is not None and latency > 3000:
        infra -= 10
        factors_negative.append(f"Slow response: {latency}ms")

    scores['infra'] = clamp(infra)

    # --- Security Score (weight 0.15) ---
    sec = 50
    if ssl_data.get('has_ssl'):
        sec += 20
        factors_positive.append(f"SSL: {ssl_data.get('issuer', 'present')}")
    else:
        sec -= 30
        factors_negative.append("No SSL certificate")

    if ssl_data.get('expired'):
        sec -= 30
        factors_negative.append("SSL certificate EXPIRED")
    if ssl_data.get('self_signed'):
        sec -= 20
        factors_negative.append("Self-signed SSL certificate")

    cert_type = ssl_data.get('cert_type', 'unknown')
    if cert_type == 'EV':
        sec += 15
        factors_positive.append("Extended Validation (EV) certificate")
    elif cert_type == 'OV':
        sec += 10
        factors_positive.append("Organization Validated (OV) certificate")

    tls = ssl_data.get('tls_versions', [])
    tls_str = ' '.join(tls).lower()
    if '1.3' in tls_str or 'tlsv1.3' in tls_str:
        sec += 5
    if '1.0' in tls_str or '1.1' in tls_str:
        if 'tlsv1.0' in tls_str or 'tls 1.0' in tls_str or 'tlsv1.1' in tls_str or 'tls 1.1' in tls_str:
            sec -= 10
            factors_negative.append("Outdated TLS 1.0/1.1 supported")

    sec_headers = security.get('security_headers_count', 0)
    if sec_headers >= 4:
        sec += 10
        factors_positive.append(f"Security headers: {sec_headers}/6 present")
    elif sec_headers <= 1:
        sec -= 10
        factors_negative.append(f"Missing security headers ({6 - sec_headers}/6)")

    if security.get('spamhaus_dbl'):
        sec -= 30
        factors_negative.append("Listed in Spamhaus DBL (spam blacklist)")

    # New security params
    if security.get('hsts_enabled'):
        sec += 5
        if security.get('hsts_preload'):
            sec += 3
            factors_positive.append("HSTS preload enabled")
    if security.get('has_robots_txt'):
        sec += 3
    if security.get('has_sitemap'):
        sec += 3
    if security.get('robots_disallow_all'):
        sec -= 5
        factors_negative.append("robots.txt blocks all crawlers")
    if security.get('mixed_content_risk'):
        sec -= 8
        factors_negative.append("Mixed content (HTTP resources on HTTPS)")
    if security.get('has_payment_form') and not ssl_data.get('has_ssl'):
        sec -= 15
        factors_negative.append("Payment form without SSL!")
    if security.get('x_powered_by'):
        sec -= 2  # minor: info disclosure
    if security.get('has_secure_cookies'):
        sec += 3
    if security.get('has_httponly_cookies'):
        sec += 2

    scores['security'] = clamp(sec)

    # --- Legal Score (weight 0.18) ---
    leg = 0
    if legal.get('tos_exists'):
        leg += 15
        factors_positive.append("Terms of Service page found")
    else:
        factors_negative.append("No Terms of Service found")
    if legal.get('privacy_exists'):
        leg += 15
        factors_positive.append("Privacy Policy page found")
    else:
        factors_negative.append("No Privacy Policy found")

    if legal.get('company_name'):
        leg += 20
        factors_positive.append(f"Company identified: {legal['company_name']}")
    if legal.get('registration_number'):
        leg += 15
    if legal.get('jurisdiction'):
        leg += 10
    if legal.get('license_number'):
        leg += 10
        factors_positive.append(f"License: {legal['license_number']}")
    if legal.get('contact_email'):
        leg += 5
    if legal.get('contact_phone'):
        leg += 5
    social = legal.get('social_links', {})
    if len(social) >= 2:
        leg += 5
        factors_positive.append(f"Social media: {', '.join(social.keys())}")

    scores['legal'] = clamp(leg)

    # --- Tech Score (weight 0.08) ---
    tsc = 50
    if tech.get('cms'):
        tsc += 10
    if tech.get('payment_integrations'):
        tsc += 10
        factors_positive.append(f"Payment: {', '.join(tech['payment_integrations'])}")
    if tech.get('google_analytics_ids') or tech.get('yandex_metrica_ids'):
        tsc += 10
        factors_positive.append("Analytics tracking installed")
    if tech.get('chat_widget'):
        tsc += 5

    scores['tech'] = clamp(tsc)

    # --- Reputation Score (weight 0.17) ---
    # Base: use domain age as proxy when Wayback data unavailable
    age_days = domain.get('age_days') or 0
    if age_days >= 1095:
        rep = 50  # 3+ years old -> baseline trust even without Wayback
    elif age_days >= 365:
        rep = 40
    elif age_days >= 90:
        rep = 35
    else:
        rep = 20

    wb_count = reputation.get('wayback_snapshots_count', 0)
    if wb_count > 50:
        rep += 25
        factors_positive.append(f"Wayback Machine: {wb_count} snapshots")
    elif wb_count > 10:
        rep += 15
    elif wb_count > 0:
        rep += 5
    elif age_days < 365:
        # Only penalize lack of Wayback for young domains
        factors_negative.append("No Wayback Machine history")

    wb_first = reputation.get('wayback_first_snapshot')
    if wb_first:
        try:
            year = int(wb_first[:4])
            from datetime import datetime
            years_ago = datetime.now().year - year
            if years_ago >= 5:
                rep += 25
                factors_positive.append(f"First archived: {year} ({years_ago}+ years ago)")
            elif years_ago >= 1:
                rep += 10
        except (ValueError, TypeError):
            pass

    scores['reputation'] = clamp(rep)

    # --- Relations Score (weight 0.10) ---
    # placeholder - graph not populated yet for standalone scan
    scores['relations'] = 50

    # --- Weighted Sum ---
    weights = {
        'domain': 0.20,
        'infra': 0.12,
        'security': 0.15,
        'legal': 0.18,
        'tech': 0.08,
        'reputation': 0.17,
        'relations': 0.10,
    }

    raw_score = sum(scores[k] * weights[k] for k in weights)
    raw_score = clamp(raw_score)

    # --- Critical Overrides ---
    overrides_applied = []
    final_score = raw_score

    if security.get('spamhaus_dbl'):
        if final_score > 30:
            final_score = 30
            overrides_applied.append('spamhaus_dbl -> cap 30')

    if ssl_data.get('expired') or ssl_data.get('self_signed'):
        if final_score > 40:
            final_score = 40
            overrides_applied.append('ssl_expired_or_selfsigned -> cap 40')

    age = domain.get('age_days') or 999
    if age < 30 and domain.get('whois_privacy'):
        if final_score > 45:
            final_score = 45
            overrides_applied.append('new_domain_with_privacy -> cap 45')

    if not ssl_data.get('has_ssl'):
        if final_score > 50:
            final_score = 50
            overrides_applied.append('no_ssl -> cap 50')

    # --- Color/Level ---
    if final_score >= 85:
        level, color = 'trusted', 'green'
    elif final_score >= 75:
        level, color = 'mostly_ok', 'yellow_green'
    elif final_score >= 60:
        level, color = 'caution', 'yellow'
    elif final_score >= 40:
        level, color = 'high_risk', 'orange'
    else:
        level, color = 'danger', 'red'

    # Top factors
    top_pos = factors_positive[:5]
    top_neg = factors_negative[:5]

    return {
        'total_score': final_score,
        'raw_score': raw_score,
        'level': level,
        'color': color,
        'breakdown': scores,
        'weights': weights,
        'overrides_applied': overrides_applied,
        'top_positive': top_pos,
        'top_negative': top_neg,
    }
