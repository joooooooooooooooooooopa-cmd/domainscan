"""DomainScan API server — serves frontend + scan API + auth + PDF."""
import asyncio
import sys
import os
import hashlib
import secrets
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.scanner.pipeline import run_scan
from core.shared.validators import normalize_and_validate
from core.reports.pdf_report import generate_pdf

app = FastAPI(title="DomainScan API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"

# === In-memory storage (replace with PostgreSQL in production) ===
JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_hex(32))
_users = {}          # email -> {password_hash, name, created_at, scans_today, last_scan_date}
_tokens = {}         # token -> {email, expires}
_scan_cache = {}     # scan_id -> full scan result (for PDF download)
_scan_counter = 0
FREE_DAILY_LIMIT = 3


def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _make_token(email: str) -> str:
    token = secrets.token_urlsafe(32)
    _tokens[token] = {"email": email, "expires": time.time() + 86400 * 7}
    return token


def _get_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "")
    t = _tokens.get(token)
    if not t or t["expires"] < time.time():
        return None
    return _users.get(t["email"])


class ScanRequest(BaseModel):
    domain: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str


# === AUTH ENDPOINTS ===

@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    email = req.email.strip().lower()
    if not email or '@' not in email or len(req.password) < 6:
        raise HTTPException(400, "Invalid email or password (min 6 chars)")
    if email in _users:
        raise HTTPException(409, "Email already registered")
    _users[email] = {
        "password_hash": _hash_pw(req.password),
        "name": req.name or email.split("@")[0],
        "created_at": datetime.utcnow().isoformat(),
        "scans_today": 0,
        "last_scan_date": "",
        "history": [],
    }
    token = _make_token(email)
    return {"token": token, "name": _users[email]["name"], "email": email}


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    email = req.email.strip().lower()
    user = _users.get(email)
    if not user or user["password_hash"] != _hash_pw(req.password):
        raise HTTPException(401, "Invalid email or password")
    token = _make_token(email)
    return {"token": token, "name": user["name"], "email": email}


@app.get("/api/auth/me")
async def me(authorization: Optional[str] = Header(None)):
    user = _get_user(authorization)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return {"name": user["name"], "email": next(e for e, u in _users.items() if u is user),
            "history": user.get("history", [])[-20:]}


# === PDF ENDPOINT ===

@app.get("/api/report/{scan_id}/pdf")
async def download_pdf(scan_id: str):
    data = _scan_cache.get(scan_id)
    if not data:
        raise HTTPException(404, "Scan not found. Reports available for 1 hour after scan.")
    pdf_bytes = generate_pdf(data)
    domain = data.get("domain", "scan")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="DomainScan_{domain}.pdf"'}
    )


# === SCAN ENDPOINT ===

@app.post("/api/scan")
async def api_scan(req: ScanRequest, authorization: Optional[str] = Header(None)):
    global _scan_counter
    try:
        domain = normalize_and_validate(req.domain)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        report = await asyncio.wait_for(run_scan(domain), timeout=60)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Scan timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)[:200]}")

    ts = report["trust_score"]
    checks = report["checks"]
    dc = checks.get("domain_check", {})
    dns_d = checks.get("dns_check", {})
    ssl_d = checks.get("ssl_check", {})
    sec = checks.get("security_check", {})
    leg = checks.get("legal_check", {})
    tech = checks.get("tech_check", {})
    rep = checks.get("reputation_check", {})

    # Build factor pills
    pills = []
    if ssl_d.get("has_ssl"):
        ct = ssl_d.get("cert_type", "DV")
        pills.append({"text": f"SSL · {ct}", "ok": True})
    else:
        pills.append({"text": "Нет SSL", "ok": False})

    age = dc.get("age_days")
    if age and age >= 365:
        pills.append({"text": f"{age // 365} лет", "ok": True})
    elif age is not None:
        pills.append({"text": f"{age} дней", "ok": age >= 90})

    if dns_d.get("cdn_detected"):
        pills.append({"text": dns_d["cdn_detected"], "ok": True})
    elif dns_d.get("cloud_provider"):
        pills.append({"text": dns_d["cloud_provider"], "ok": True})

    if dc.get("dnssec_enabled"):
        pills.append({"text": "DNSSEC", "ok": True})

    if leg.get("tos_exists"):
        pills.append({"text": "Terms of Service", "ok": True})
    else:
        pills.append({"text": "Нет ToS", "ok": False})

    if leg.get("privacy_exists"):
        pills.append({"text": "Privacy Policy", "ok": True})
    else:
        pills.append({"text": "Нет Privacy", "ok": False})

    if dc.get("whois_privacy"):
        pills.append({"text": "WHOIS скрыт", "ok": False})

    if sec.get("hsts_enabled"):
        pills.append({"text": "HSTS", "ok": True})
    if sec.get("has_robots_txt"):
        pills.append({"text": "robots.txt", "ok": True})
    if sec.get("has_sitemap"):
        pills.append({"text": "Sitemap", "ok": True})
    if dns_d.get("has_spf"):
        pills.append({"text": "SPF", "ok": True})
    if dns_d.get("has_dmarc"):
        pills.append({"text": f"DMARC ({dns_d.get('dmarc_policy', '?')})", "ok": True})
    if dns_d.get("has_ipv6"):
        pills.append({"text": "IPv6", "ok": True})
    if sec.get("mixed_content_risk"):
        pills.append({"text": "Mixed content!", "ok": False})

    if sec.get("spamhaus_dbl"):
        pills.append({"text": "В чёрном списке!", "ok": False})

    # Details for full report
    details = {
        "domain": {
            "age_days": dc.get("age_days"),
            "created_at": (dc.get("created_at") or "")[:10],
            "registrar": dc.get("registrar_name"),
            "registrar_risk": dc.get("registrar_risk"),
            "tld_risk": dc.get("tld_risk"),
            "whois_privacy": dc.get("whois_privacy"),
            "dnssec": dc.get("dnssec_enabled"),
        },
        "dns": {
            "ip": dns_d.get("a_records", [])[:3],
            "ipv6": dns_d.get("has_ipv6"),
            "country": dns_d.get("country"),
            "city": dns_d.get("city"),
            "asn_org": (dns_d.get("asn_org") or "")[:50],
            "cdn": dns_d.get("cdn_detected"),
            "cloud": dns_d.get("cloud_provider"),
            "mx_provider": dns_d.get("mx_provider"),
            "latency_ms": dns_d.get("response_time_ms"),
            "cf_ns_pair": dns_d.get("cloudflare_ns_pair"),
            "ns_count": dns_d.get("ns_count", 0),
            "spf": dns_d.get("has_spf"),
            "spf_strict": dns_d.get("spf_strict"),
            "dmarc": dns_d.get("has_dmarc"),
            "dmarc_policy": dns_d.get("dmarc_policy"),
        },
        "ssl": {
            "has_ssl": ssl_d.get("has_ssl"),
            "issuer": ssl_d.get("issuer"),
            "cert_type": ssl_d.get("cert_type"),
            "expired": ssl_d.get("expired"),
            "valid_to": (ssl_d.get("valid_to") or "")[:10],
            "tls": ssl_d.get("tls_versions", []),
            "san_count": len(ssl_d.get("san", [])),
            "ct_certs": ssl_d.get("cert_history_count", 0),
            "ct_subdomains": len(ssl_d.get("subdomains_from_ct", [])),
        },
        "security": {
            "spamhaus": sec.get("spamhaus_dbl"),
            "headers_count": sec.get("security_headers_count", 0),
            "headers_missing": sec.get("security_headers_missing", []),
            "hsts": sec.get("hsts_enabled"),
            "hsts_preload": sec.get("hsts_preload"),
            "robots_txt": sec.get("has_robots_txt"),
            "sitemap": sec.get("has_sitemap"),
            "mixed_content": sec.get("mixed_content_risk"),
            "login_form": sec.get("has_login_form"),
            "payment_form": sec.get("has_payment_form"),
            "redirect_count": sec.get("redirect_count", 0),
            "cookies": sec.get("cookie_count", 0),
            "server": sec.get("server_header"),
        },
        "legal": {
            "tos": leg.get("tos_exists"),
            "privacy": leg.get("privacy_exists"),
            "company": leg.get("company_name"),
            "reg_number": leg.get("registration_number"),
            "jurisdiction": leg.get("jurisdiction"),
            "email": leg.get("contact_email"),
            "phone": leg.get("contact_phone"),
            "social": list(leg.get("social_links", {}).keys()),
        },
        "tech": {
            "cms": tech.get("cms"),
            "framework": tech.get("frontend_framework"),
            "analytics": tech.get("google_analytics_ids", []) + tech.get("yandex_metrica_ids", []),
            "payments": tech.get("payment_integrations", []),
            "chat": tech.get("chat_widget"),
        },
        "reputation": {
            "wayback_count": rep.get("wayback_snapshots_count", 0),
            "wayback_first": rep.get("wayback_first_snapshot"),
        },
    }

    # Store for PDF download
    _scan_counter += 1
    scan_id = f"{_scan_counter}-{secrets.token_hex(4)}"
    _scan_cache[scan_id] = report

    # Clean old scans (keep last 100)
    if len(_scan_cache) > 100:
        oldest = list(_scan_cache.keys())[:50]
        for k in oldest:
            _scan_cache.pop(k, None)

    # Save to user history if authenticated
    user = _get_user(authorization)
    if user is not None:
        user.setdefault("history", []).append({
            "scan_id": scan_id,
            "domain": domain,
            "score": ts["total_score"],
            "level": ts["level"],
            "time": datetime.utcnow().isoformat(),
        })
        if len(user["history"]) > 50:
            user["history"] = user["history"][-50:]

    return {
        "scan_id": scan_id,
        "domain": domain,
        "score": ts["total_score"],
        "level": ts["level"],
        "color": ts["color"],
        "breakdown": ts["breakdown"],
        "top_positive": ts["top_positive"],
        "top_negative": ts["top_negative"],
        "overrides": ts["overrides_applied"],
        "pills": pills,
        "details": details,
        "duration_ms": report["duration_ms"],
    }


# Serve static files at root — must be LAST (after /api routes)
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
