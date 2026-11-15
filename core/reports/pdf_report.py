"""PDF report generator for DomainScan."""
import io
from datetime import datetime
from fpdf import FPDF


class ScanPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(30, 64, 175)
        self.cell(0, 8, 'DomainScan Report', align='L')
        self.set_font('Helvetica', '', 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, datetime.now().strftime('%d.%m.%Y %H:%M UTC'), align='R')
        self.ln(10)
        self.set_draw_color(219, 234, 254)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f'DomainScan - Trust Score is an algorithmic assessment, not a legal verdict. Page {self.page_no()}', align='C')


def generate_pdf(scan_result: dict) -> bytes:
    ts = scan_result['trust_score']
    checks = scan_result['checks']
    domain = scan_result['domain']
    duration = scan_result.get('duration_ms', 0)

    dc = checks.get('domain_check', {})
    dns_d = checks.get('dns_check', {})
    ssl_d = checks.get('ssl_check', {})
    sec = checks.get('security_check', {})
    leg = checks.get('legal_check', {})
    tech = checks.get('tech_check', {})
    rep = checks.get('reputation_check', {})

    pdf = ScanPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # === TITLE ===
    pdf.set_font('Helvetica', 'B', 22)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 12, domain, ln=True)

    # === TRUST SCORE ===
    score = ts['total_score']
    level = ts['level']
    level_ru = {'trusted': 'TRUSTED', 'mostly_ok': 'MOSTLY OK', 'caution': 'CAUTION',
                'high_risk': 'HIGH RISK', 'danger': 'DANGER'}.get(level, level)

    colors = {'trusted': (34, 197, 94), 'mostly_ok': (132, 204, 22), 'caution': (234, 179, 8),
              'high_risk': (249, 115, 22), 'danger': (239, 68, 68)}
    sc = colors.get(level, (100, 100, 100))

    pdf.set_font('Helvetica', 'B', 48)
    pdf.set_text_color(*sc)
    pdf.cell(50, 25, str(score), ln=False)
    pdf.set_font('Helvetica', '', 14)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(15, 25, '/ 100', ln=False)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*sc)
    pdf.cell(0, 25, level_ru, ln=True)

    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, f'Scanned in {round(duration / 1000, 1)}s | {datetime.now().strftime("%d %b %Y %H:%M")}', ln=True)
    pdf.ln(6)

    # === BREAKDOWN ===
    _section(pdf, 'Category Breakdown')
    cat_names = {'domain': 'Domain', 'infra': 'Infrastructure', 'security': 'Security',
                 'legal': 'Legal', 'tech': 'Technology', 'reputation': 'Reputation', 'relations': 'Graph'}
    weights = ts.get('weights', {})

    for cat, val in ts.get('breakdown', {}).items():
        name = cat_names.get(cat, cat)
        weight = weights.get(cat, 0)
        if val >= 70:
            c = (34, 197, 94)
        elif val >= 40:
            c = (234, 179, 8)
        else:
            c = (239, 68, 68)

        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(45, 6, name, ln=False)

        # Bar
        x = pdf.get_x()
        y = pdf.get_y()
        bar_w = 80
        pdf.set_fill_color(241, 245, 249)
        pdf.rect(x, y + 1, bar_w, 4, 'F')
        pdf.set_fill_color(*c)
        pdf.rect(x, y + 1, bar_w * val / 100, 4, 'F')

        pdf.set_x(x + bar_w + 3)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*c)
        pdf.cell(15, 6, str(val), ln=False)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(0, 6, f'({int(weight * 100)}%)', ln=True)

    pdf.ln(4)

    # === FACTORS ===
    if ts.get('top_positive'):
        _section(pdf, 'Positive Factors')
        for f in ts['top_positive']:
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(34, 197, 94)
            pdf.cell(6, 5, '+', ln=False)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(0, 5, _safe(f), ln=True)

    if ts.get('top_negative'):
        _section(pdf, 'Negative Factors')
        for f in ts['top_negative']:
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(239, 68, 68)
            pdf.cell(6, 5, '-', ln=False)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(0, 5, _safe(f), ln=True)

    if ts.get('overrides_applied'):
        _section(pdf, 'Critical Overrides')
        for o in ts['overrides_applied']:
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(249, 115, 22)
            pdf.cell(6, 5, '!', ln=False)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(0, 5, _safe(o), ln=True)

    pdf.ln(4)

    # === DOMAIN ===
    _section(pdf, 'Domain & Registration')
    _kv(pdf, 'Age', f"{dc.get('age_days', '?')} days" + (f" (registered {(dc.get('created_at') or '?')[:10]})" if dc.get('created_at') else ''))
    _kv(pdf, 'Registrar', f"{dc.get('registrar_name', '?')} ({dc.get('registrar_risk', '?')})")
    _kv(pdf, 'TLD Risk', dc.get('tld_risk', '?'))
    _kv(pdf, 'WHOIS Privacy', 'Yes' if dc.get('whois_privacy') else 'No')
    _kv(pdf, 'DNSSEC', 'Yes' if dc.get('dnssec_enabled') else 'No')

    # === DNS ===
    _section(pdf, 'Infrastructure & DNS')
    _kv(pdf, 'IP', ', '.join(dns_d.get('a_records', [])[:3]) or '?')
    _kv(pdf, 'Country', f"{dns_d.get('country', '?')} | {dns_d.get('city', '?')}")
    _kv(pdf, 'ASN', (dns_d.get('asn_org') or '?')[:50])
    _kv(pdf, 'CDN', dns_d.get('cdn_detected') or 'None')
    _kv(pdf, 'Cloud', dns_d.get('cloud_provider') or '?')
    _kv(pdf, 'MX', dns_d.get('mx_provider') or 'None')
    _kv(pdf, 'Latency', f"{dns_d.get('response_time_ms', '?')}ms")
    _kv(pdf, 'IPv6', 'Yes' if dns_d.get('has_ipv6') else 'No')
    _kv(pdf, 'SPF', ('Yes (strict)' if dns_d.get('spf_strict') else 'Yes') if dns_d.get('has_spf') else 'No')
    _kv(pdf, 'DMARC', f"Yes ({dns_d.get('dmarc_policy', '?')})" if dns_d.get('has_dmarc') else 'No')

    # === SSL ===
    _section(pdf, 'SSL / TLS')
    _kv(pdf, 'SSL', 'Yes' if ssl_d.get('has_ssl') else 'NO')
    if ssl_d.get('has_ssl'):
        _kv(pdf, 'Issuer', f"{ssl_d.get('issuer', '?')} ({ssl_d.get('cert_type', '?')})")
        _kv(pdf, 'Valid To', (ssl_d.get('valid_to') or '?')[:10])
        _kv(pdf, 'TLS', ', '.join(ssl_d.get('tls_versions', [])) or '?')
        _kv(pdf, 'SAN', f"{len(ssl_d.get('san', []))} domains")
        _kv(pdf, 'CT Certs', str(ssl_d.get('cert_history_count', 0)))

    # === SECURITY ===
    _section(pdf, 'Security')
    _kv(pdf, 'Spamhaus', 'LISTED!' if sec.get('spamhaus_dbl') else 'Clean')
    _kv(pdf, 'Headers', f"{sec.get('security_headers_count', 0)}/6")
    _kv(pdf, 'HSTS', 'Yes' + (' (preload)' if sec.get('hsts_preload') else '') if sec.get('hsts_enabled') else 'No')
    _kv(pdf, 'robots.txt', 'Yes' if sec.get('has_robots_txt') else 'No')
    _kv(pdf, 'Sitemap', 'Yes' if sec.get('has_sitemap') else 'No')
    _kv(pdf, 'Mixed Content', 'YES (risk!)' if sec.get('mixed_content_risk') else 'No')
    _kv(pdf, 'Login Form', 'Yes' if sec.get('has_login_form') else 'No')
    _kv(pdf, 'Cookies', str(sec.get('cookie_count', 0)))

    # === LEGAL ===
    _section(pdf, 'Legal Transparency')
    _kv(pdf, 'ToS', 'Found' if leg.get('tos_exists') else 'Not found')
    _kv(pdf, 'Privacy', 'Found' if leg.get('privacy_exists') else 'Not found')
    _kv(pdf, 'Company', leg.get('company_name') or 'Not found')
    _kv(pdf, 'Reg. Number', leg.get('registration_number') or 'Not found')
    _kv(pdf, 'Jurisdiction', leg.get('jurisdiction') or '?')
    _kv(pdf, 'Email', leg.get('contact_email') or '-')
    _kv(pdf, 'Phone', leg.get('contact_phone') or '-')
    social = leg.get('social_links', {})
    if social:
        _kv(pdf, 'Social', ', '.join(social.keys()))

    # === TECH ===
    _section(pdf, 'Technology')
    _kv(pdf, 'CMS', tech.get('cms') or '-')
    _kv(pdf, 'Framework', tech.get('frontend_framework') or '-')
    ga = tech.get('google_analytics_ids', [])
    ym = tech.get('yandex_metrica_ids', [])
    if ga:
        _kv(pdf, 'Google Analytics', ', '.join(ga))
    if ym:
        _kv(pdf, 'Yandex Metrica', ', '.join(ym))
    pays = tech.get('payment_integrations', [])
    if pays:
        _kv(pdf, 'Payments', ', '.join(pays))
    if tech.get('chat_widget'):
        _kv(pdf, 'Chat', tech['chat_widget'])
    if tech.get('favicon_hash'):
        _kv(pdf, 'Favicon Hash', tech['favicon_hash'])

    # === REPUTATION ===
    _section(pdf, 'Reputation')
    _kv(pdf, 'Wayback', f"{rep.get('wayback_snapshots_count', 0)} snapshots")
    if rep.get('wayback_first_snapshot'):
        _kv(pdf, 'First Archived', rep['wayback_first_snapshot'][:8])

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf.getvalue()


def _section(pdf, title):
    pdf.ln(3)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(0, 7, title, ln=True)
    pdf.set_draw_color(219, 234, 254)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)


def _kv(pdf, key, val):
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(40, 5, key, ln=False)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 5, _safe(str(val)), ln=True)


def _safe(text):
    return text.encode('latin-1', errors='replace').decode('latin-1')
