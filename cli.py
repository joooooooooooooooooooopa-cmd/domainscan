#!/usr/bin/env python3
"""DomainScan CLI - scan a domain and print Trust Score report."""
import asyncio
import sys
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from core.scanner.pipeline import run_scan

console = Console()

SCORE_COLORS = {
    'green': '[bold green]',
    'yellow_green': '[bold yellow]',
    'yellow': '[bold yellow]',
    'orange': '[bold dark_orange]',
    'red': '[bold red]',
}

LEVEL_LABELS = {
    'trusted': 'TRUSTED',
    'mostly_ok': 'MOSTLY OK',
    'caution': 'CAUTION',
    'high_risk': 'HIGH RISK',
    'danger': 'DANGER',
}


async def main_async(domain: str):
    # Validation happens inside run_scan via normalize_and_validate
    console.print(f"\n[bold blue]DomainScan[/] scanning [bold]{domain}[/]...\n")

    with console.status("[bold blue]Scanning...", spinner="dots"):
        report = await run_scan(domain)

    ts = report['trust_score']
    score = ts['total_score']
    color = SCORE_COLORS.get(ts['color'], '[bold white]')
    level = LEVEL_LABELS.get(ts['level'], ts['level'])

    # Score header
    score_text = f"{color}{score}/100 - {level}[/]"
    console.print(Panel(
        f"[bold]Trust Score: {score_text}",
        title=f"[bold blue]{domain}[/]",
        subtitle=f"Scanned in {report['duration_ms']}ms",
        border_style="blue",
    ))

    # Category breakdown
    table = Table(title="Category Breakdown", box=box.ROUNDED, border_style="blue")
    table.add_column("Category", style="bold")
    table.add_column("Score", justify="center")
    table.add_column("Weight", justify="center")
    table.add_column("Contribution", justify="center")

    for cat, weight in ts['weights'].items():
        cat_score = ts['breakdown'].get(cat, 0)
        contribution = round(cat_score * weight, 1)
        if cat_score >= 70:
            style = "green"
        elif cat_score >= 40:
            style = "yellow"
        else:
            style = "red"
        table.add_row(
            cat.capitalize(),
            f"[{style}]{cat_score}[/]",
            f"{int(weight * 100)}%",
            f"{contribution}",
        )
    console.print(table)

    # Positive factors
    if ts['top_positive']:
        console.print("\n[bold green]+ Positive Factors:[/]")
        for f in ts['top_positive']:
            console.print(f"  [green]+[/] {f}")

    # Negative factors
    if ts['top_negative']:
        console.print("\n[bold red]- Negative Factors:[/]")
        for f in ts['top_negative']:
            console.print(f"  [red]-[/] {f}")

    # Overrides
    if ts['overrides_applied']:
        console.print("\n[bold dark_orange]! Critical Overrides:[/]")
        for o in ts['overrides_applied']:
            console.print(f"  [dark_orange]![/] {o}")

    # Key details
    checks = report['checks']

    console.print("\n[bold blue]--- Key Details ---[/]")

    d = checks.get('domain_check', {})
    if d.get('age_days') is not None:
        created = (d.get('created_at') or '?')[:10]
        console.print(f"  Domain age: [bold]{d['age_days']}[/] days (registered: {created})")
    console.print(f"  Registrar: {d.get('registrar_name', '?')} (risk: {d.get('registrar_risk', '?')})")
    console.print(f"  TLD risk: {d.get('tld_risk', '?')} (.{d.get('tld', '?')})")
    console.print(f"  WHOIS privacy: {'Yes' if d.get('whois_privacy') else 'No'}")
    console.print(f"  DNSSEC: {'Yes' if d.get('dnssec_enabled') else 'No'}")

    dns_d = checks.get('dns_check', {})
    console.print(f"\n  IP: {', '.join(dns_d.get('a_records', ['?']))}")
    console.print(f"  Country: {dns_d.get('country', '?')} | City: {dns_d.get('city', '?')}")
    console.print(f"  ASN: {dns_d.get('asn_org', '?')}")
    console.print(f"  CDN: {dns_d.get('cdn_detected', 'None')}")
    console.print(f"  Cloud: {dns_d.get('cloud_provider', 'Unknown')}")
    console.print(f"  MX: {dns_d.get('mx_provider', 'None')} ({', '.join(dns_d.get('mx_records', [])[:2])})")
    console.print(f"  Latency: {dns_d.get('response_time_ms', '?')}ms")

    ssl_d = checks.get('ssl_check', {})
    console.print(f"\n  SSL: {'Yes' if ssl_d.get('has_ssl') else 'NO'}")
    if ssl_d.get('has_ssl'):
        console.print(f"  Issuer: {ssl_d.get('issuer', '?')} ({ssl_d.get('cert_type', '?')})")
        vf = (ssl_d.get('valid_from') or '?')[:10]
        vt = (ssl_d.get('valid_to') or '?')[:10]
        console.print(f"  Valid: {vf} to {vt}")
        console.print(f"  TLS: {', '.join(ssl_d.get('tls_versions', []))}")
        console.print(f"  crt.sh: {ssl_d.get('cert_history_count', 0)} certs, {len(ssl_d.get('subdomains_from_ct', []))} subdomains")

    sec = checks.get('security_check', {})
    console.print(f"\n  Spamhaus DBL: {'LISTED!' if sec.get('spamhaus_dbl') else 'Clean'}")
    console.print(f"  Security headers: {sec.get('security_headers_count', 0)}/6")

    legal_d = checks.get('legal_check', {})
    console.print(f"\n  ToS: {'Found' if legal_d.get('tos_exists') else 'Not found'}")
    console.print(f"  Privacy: {'Found' if legal_d.get('privacy_exists') else 'Not found'}")
    console.print(f"  Company: {legal_d.get('company_name', 'Not found')}")
    console.print(f"  Reg. number: {legal_d.get('registration_number', 'Not found')}")
    console.print(f"  Jurisdiction: {legal_d.get('jurisdiction', 'Unknown')}")
    console.print(f"  Email: {legal_d.get('contact_email', 'Not found')}")
    console.print(f"  Phone: {legal_d.get('contact_phone', 'Not found')}")
    social = legal_d.get('social_links', {})
    if social:
        console.print(f"  Social: {', '.join(social.keys())}")

    tech_d = checks.get('tech_check', {})
    console.print(f"\n  CMS: {tech_d.get('cms', 'Unknown')}")
    console.print(f"  Framework: {tech_d.get('frontend_framework', 'Unknown')}")
    if tech_d.get('google_analytics_ids'):
        console.print(f"  Google Analytics: {', '.join(tech_d['google_analytics_ids'])}")
    if tech_d.get('yandex_metrica_ids'):
        console.print(f"  Yandex Metrica: {', '.join(tech_d['yandex_metrica_ids'])}")
    if tech_d.get('payment_integrations'):
        console.print(f"  Payments: {', '.join(tech_d['payment_integrations'])}")
    if tech_d.get('favicon_hash'):
        console.print(f"  Favicon hash: {tech_d['favicon_hash']}")

    rep = checks.get('reputation_check', {})
    console.print(f"\n  Wayback: {rep.get('wayback_snapshots_count', 0)} snapshots")
    if rep.get('wayback_first_snapshot'):
        console.print(f"  First archived: {rep['wayback_first_snapshot'][:6]}")

    # JSON flag
    if '--json' in sys.argv:
        console.print("\n[dim]--- Raw JSON ---[/]")
        console.print(json.dumps(report, indent=2, default=str, ensure_ascii=False))

    console.print()


def main():
    # --help не должен уходить в сканер как «домен» и дёргать сеть
    if len(sys.argv) >= 2 and sys.argv[1] in ('-h', '--help'):
        console.print("[bold]Usage:[/] python3 cli.py <domain> [--json]")
        console.print("  Example: python3 cli.py example.com")
        sys.exit(0)
    if len(sys.argv) < 2:
        console.print("[bold red]Usage:[/] python3 cli.py <domain> [--json]")
        console.print("  Example: python3 cli.py example.com")
        sys.exit(1)

    domain = sys.argv[1]
    asyncio.run(main_async(domain))


if __name__ == '__main__':
    main()
