// DomainScan landing — interactivity
(() => {
  // ===== Sticky nav shadow =====
  const nav = document.getElementById('nav');
  if (nav) {
    const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 12);
    window.addEventListener('scroll', onScroll, {passive:true});
    onScroll();
  }

  // ===== Reveal on scroll =====
  const revealEls = Array.from(document.querySelectorAll('section'));
  revealEls.forEach(el => el.classList.add('reveal'));
  const heroSec = document.querySelector('.hero');
  if (heroSec) heroSec.classList.add('in'); // hero visible immediately

  const revealIo = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('in');
        revealIo.unobserve(e.target);
      }
    });
  }, {threshold: 0.08, rootMargin: '-40px 0px'});
  revealEls.forEach(el => { if (el !== heroSec) revealIo.observe(el); });

  // ===== Hero scan beam — follow mouse softly (throttled) =====
  const scanBeam = document.querySelector('.scan-beam');
  if (scanBeam) {
    let raf = 0, tx = 50, ty = 30, cx = 50, cy = 30, moving = false;
    document.querySelector('.hero')?.addEventListener('mousemove', (e) => {
      const r = scanBeam.getBoundingClientRect();
      tx = ((e.clientX - r.left) / r.width) * 100;
      ty = ((e.clientY - r.top) / r.height) * 100;
      if (!moving){ moving = true; tick(); }
    });
    const tick = () => {
      const dx = tx - cx, dy = ty - cy;
      cx += dx * 0.12;
      cy += dy * 0.12;
      scanBeam.style.setProperty('--bx', cx + '%');
      scanBeam.style.setProperty('--by', cy + '%');
      if (Math.abs(dx) > 0.05 || Math.abs(dy) > 0.05){
        raf = requestAnimationFrame(tick);
      } else { moving = false; }
    };
  }

  // ===== Counter =====
  const fmt = (n) => n.toLocaleString('ru-RU');
  const animateCount = (el) => {
    const target = +el.dataset.count;
    const dur = 1800;
    const start = performance.now();
    const tick = (t) => {
      const p = Math.min(1, (t - start)/dur);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(Math.round(target * eased));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  const counters = document.querySelectorAll('.counter');
  const counterIo = new IntersectionObserver((es) => {
    es.forEach(e => { if (e.isIntersecting){ animateCount(e.target); counterIo.unobserve(e.target);} });
  }, {threshold: 0.4});
  counters.forEach(c => counterIo.observe(c));

  // ===== Hero result mockup — animate ring + bars + score =====
  const ringEl = document.getElementById('rmRing');
  const scoreEl = document.getElementById('rmScore');
  const bars = document.querySelectorAll('.rm-bars .bar');
  const animateScore = () => {
    const target = 75; // shop.example.com mock
    // ring: dasharray=314 (2*pi*r approx for r=50); offset for score
    const circ = 2 * Math.PI * 50; // 314.16
    const offset = circ * (1 - target/100);
    if (ringEl){
      ringEl.style.transition = 'stroke-dashoffset 1.6s cubic-bezier(.2,.7,.4,1)';
      requestAnimationFrame(() => { ringEl.style.strokeDashoffset = offset; });
    }
    if (scoreEl){
      const start = performance.now();
      const dur = 1400;
      const tick = (t) => {
        const p = Math.min(1, (t - start)/dur);
        const eased = 1 - Math.pow(1 - p, 3);
        scoreEl.textContent = Math.round(target * eased);
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }
    bars.forEach((b, i) => setTimeout(() => b.classList.add('animate'), 200 + i*80));
  };
  const mockupIo = new IntersectionObserver((es) => {
    es.forEach(e => { if (e.isIntersecting){ animateScore(); mockupIo.unobserve(e.target);} });
  }, {threshold: 0.3});
  const mockup = document.getElementById('resultMockup');
  if (mockup) mockupIo.observe(mockup);

  // ===== Type animation in step 1 illustration =====
  const typed = document.querySelector('.il-typed');
  if (typed){
    const text = 'https://shop-new.example/checkout?p=42';
    let i = 0;
    const speed = 80;
    const startType = () => {
      typed.textContent = '';
      const step = () => {
        if (i <= text.length){
          typed.textContent = text.slice(0, i);
          i++;
          setTimeout(step, speed + Math.random()*60);
        } else {
          setTimeout(() => { i = 0; startType(); }, 2500);
        }
      };
      step();
    };
    const typeIo = new IntersectionObserver((es) => {
      es.forEach(e => { if (e.isIntersecting){ startType(); typeIo.unobserve(e.target);} });
    }, {threshold:.3});
    typeIo.observe(typed.closest('.step-illu'));
  }

  // ===== Comparison cards: trigger in-view + score countup =====
  const cmpCards = document.querySelectorAll('.cmp-card');
  const cmpIo = new IntersectionObserver((es) => {
    es.forEach(e => {
      if (e.isIntersecting){
        e.target.classList.add('in-view');
        // Defensive inline fallback (in case of CSS load order quirks)
        e.target.style.opacity = '1';
        e.target.style.transform = 'translateX(0)';
        const scoreEl = e.target.querySelector('.cmp-score');
        if (scoreEl){
          const target = +scoreEl.dataset.val;
          const start = performance.now();
          const dur = 1500 + (e.target.dataset.side==='right'?250:0);
          const baseDelay = e.target.dataset.side==='right' ? 250 : 0;
          setTimeout(() => {
            const tick = (t) => {
              const p = Math.min(1, (t - start - baseDelay)/dur);
              const eased = 1 - Math.pow(1 - p, 3);
              scoreEl.textContent = Math.round(target * eased);
              if (p < 1) requestAnimationFrame(tick);
            };
            requestAnimationFrame(tick);
          }, baseDelay);
        }
        cmpIo.unobserve(e.target);
      }
    });
  }, {threshold: .25});
  cmpCards.forEach(c => cmpIo.observe(c));

  // ===== Pricing toggle =====
  const billBtns = document.querySelectorAll('.bill-toggle button[data-bill]');
  billBtns.forEach(b => b.addEventListener('click', () => {
    billBtns.forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    const m = b.dataset.bill;
    document.querySelectorAll('[data-p-m]').forEach(el => {
      el.textContent = m === 'y' ? el.dataset.pY : el.dataset.pM;
    });
    document.querySelectorAll('[data-alt-m]').forEach(el => {
      el.textContent = m === 'y' ? el.dataset.altY : el.dataset.altM;
    });
  }));

  // ===== FAQ accordion =====
  document.querySelectorAll('.faq-item').forEach(item => {
    const q = item.querySelector('.faq-q');
    q.addEventListener('click', () => item.classList.toggle('open'));
  });

  // ===== REAL SCAN via API =====
  const LEVEL_RU = {trusted:'Доверять',mostly_ok:'Доверять с осторожностью',caution:'Осторожно',high_risk:'Высокий риск',danger:'Опасно'};
  const LEVEL_COLOR = {trusted:'var(--green)',mostly_ok:'var(--lime)',caution:'var(--yellow)',high_risk:'var(--orange)',danger:'var(--red)'};
  const CAT_NAMES = {domain:'Домен',infra:'Инфраструктура',security:'Безопасность',legal:'Юр. прозрачность',tech:'Технологии',reputation:'Репутация',relations:'Граф связей'};

  const handleScanSubmit = (form) => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = form.querySelector('input');
      const btn = form.querySelector('.btn-scan');
      const v = (input.value || '').trim();
      if (!v) { input.focus(); return; }

      btn.classList.add('loading');
      btn.disabled = true;

      // Show mini-game while scanning
      let game;
      try { game = showScanGame(v); } catch(ge) { game = {stop:()=>{}}; }
      const gameMinTime = new Promise(r => setTimeout(r, 3000)); // min 3s to enjoy game

      try {
        var hdrs = {'Content-Type': 'application/json'};
        if (_authToken) hdrs['Authorization'] = 'Bearer ' + _authToken;
        const [resp] = await Promise.all([
          fetch('/api/scan', {
            method: 'POST',
            headers: hdrs,
            body: JSON.stringify({domain: v})
          }),
          gameMinTime
        ]);

        game.stop();

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({detail:'Ошибка сервера'}));
          alert(err.detail || 'Ошибка');
          return;
        }

        const data = await resp.json();
        renderResult(data);

      } catch (err) {
        game.stop();
        alert('Не удалось подключиться к серверу: ' + err.message);
      } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
      }
    });
  };

  function renderResult(data) {
    const mockup = document.getElementById('resultMockup');
    if (!mockup) return;

    // Update domain name
    const rmDomain = document.getElementById('rmDomain');
    if (rmDomain) rmDomain.textContent = data.domain;

    // Update HTTPS badge
    const badge = mockup.querySelector('.rm-badge');
    if (badge) {
      const hasSSL = data.details?.ssl?.has_ssl;
      badge.textContent = hasSSL ? 'https' : 'http';
      badge.style.background = hasSSL ? 'var(--green)' : 'var(--red)';
      badge.style.color = 'white';
    }

    // Update score ring
    const score = data.score;
    const circ = 2 * Math.PI * 50;
    const offset = circ * (1 - score / 100);
    const color = LEVEL_COLOR[data.level] || 'var(--yellow)';

    if (ringEl) {
      ringEl.style.transition = 'none';
      ringEl.style.strokeDashoffset = circ;
      ringEl.style.stroke = color;
      requestAnimationFrame(() => {
        ringEl.style.transition = 'stroke-dashoffset 1.6s cubic-bezier(.2,.7,.4,1)';
        ringEl.style.strokeDashoffset = offset;
      });
    }
    if (scoreEl) {
      let cur = 0;
      const start = performance.now();
      const tick = (t) => {
        const p = Math.min(1, (t - start) / 1400);
        const eased = 1 - Math.pow(1 - p, 3);
        scoreEl.textContent = Math.round(score * eased);
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }

    // Update level text
    const levelEl = mockup.querySelector('.rm-level');
    if (levelEl) {
      levelEl.innerHTML = '<span style="color:' + color + '">' + (LEVEL_RU[data.level] || data.level) + '</span>';
    }

    // Update category bars
    const barsContainer = mockup.querySelector('.rm-bars');
    if (barsContainer && data.breakdown) {
      barsContainer.innerHTML = '';
      for (const [cat, val] of Object.entries(data.breakdown)) {
        const name = CAT_NAMES[cat] || cat;
        let barColor = 'var(--green)';
        if (val < 40) barColor = 'var(--red)';
        else if (val < 60) barColor = 'var(--orange)';
        else if (val < 75) barColor = 'var(--yellow)';

        const row = document.createElement('div');
        row.className = 'bar animate';
        row.innerHTML = '<span class="bar-label">' + name + '</span>' +
          '<span class="bar-track"><span class="bar-fill" style="width:' + val + '%;background:' + barColor + '"></span></span>' +
          '<span class="bar-val mono">' + val + '</span>';
        barsContainer.appendChild(row);
      }
    }

    // Update pills
    const pillsContainer = mockup.querySelector('.rm-pills');
    if (pillsContainer && data.pills) {
      pillsContainer.innerHTML = '';
      data.pills.forEach(p => {
        const pill = document.createElement('span');
        pill.className = 'pill-tag ' + (p.ok ? 'pill-ok' : 'pill-bad');
        pill.innerHTML = (p.ok ? '✓ ' : '✗ ') + p.text;
        pillsContainer.appendChild(pill);
      });
    }

    // Update timing
    const timeEl = mockup.querySelector('.rm-time');
    if (timeEl) timeEl.textContent = 'проверено сейчас · ' + Math.round(data.duration_ms / 1000) + ' сек';

    // PDF download button
    var pdfBtn = document.getElementById('pdfDownloadBtn');
    if (!pdfBtn) {
      pdfBtn = document.createElement('a');
      pdfBtn.id = 'pdfDownloadBtn';
      pdfBtn.style.cssText = 'display:inline-flex;align-items:center;gap:6px;padding:10px 20px;background:#1E40AF;color:#fff;border-radius:8px;font-size:14px;font-weight:600;text-decoration:none;margin-top:16px;cursor:pointer';
      pdfBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg> Скачать PDF отчёт';
      var footer = mockup.querySelector('footer');
      if (footer) footer.appendChild(pdfBtn);
    }
    if (data.scan_id) {
      pdfBtn.href = '/api/report/' + data.scan_id + '/pdf';
      pdfBtn.target = '_blank';
      pdfBtn.style.display = 'inline-flex';
    }

    // Build details section below mockup
    renderDetails(data);

    // Scroll to result
    mockup.scrollIntoView({behavior: 'smooth', block: 'start'});
  }

  function renderDetails(data) {
    let detailsEl = document.getElementById('scanDetails');
    if (!detailsEl) {
      detailsEl = document.createElement('div');
      detailsEl.id = 'scanDetails';
      detailsEl.style.cssText = 'max-width:720px;margin:32px auto 0;padding:0 24px';
      const mockup = document.getElementById('resultMockup');
      if (mockup) mockup.parentElement.insertBefore(detailsEl, mockup.nextSibling);
    }

    const d = data.details || {};
    const pos = (data.top_positive || []).map(f => '<div style="color:var(--green);padding:4px 0">✓ ' + f + '</div>').join('');
    const neg = (data.top_negative || []).map(f => '<div style="color:var(--red);padding:4px 0">✗ ' + f + '</div>').join('');
    const ov = (data.overrides || []).map(f => '<div style="color:var(--orange);padding:4px 0">⚠ ' + f + '</div>').join('');

    const dom = d.domain || {};
    const dns = d.dns || {};
    const ssl = d.ssl || {};
    const sec = d.security || {};
    const leg = d.legal || {};
    const tech = d.tech || {};
    const rep = d.reputation || {};

    detailsEl.innerHTML = `
      <div style="background:var(--ink-50);border-radius:16px;padding:28px 32px;margin-top:24px;font-size:15px;line-height:1.7">
        <h3 style="margin-bottom:16px;font-size:20px">Подробный отчёт: ${data.domain}</h3>

        ${pos ? '<div style="margin-bottom:12px">' + pos + '</div>' : ''}
        ${neg ? '<div style="margin-bottom:12px">' + neg + '</div>' : ''}
        ${ov ? '<div style="margin-bottom:12px;padding:8px 12px;background:rgba(249,115,22,.08);border-radius:8px">' + ov + '</div>' : ''}

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:20px">
          <div>
            <h4 style="color:var(--blue-800);margin-bottom:8px">🌐 Домен</h4>
            <div>Возраст: <b>${dom.age_days ? dom.age_days + ' дней' : 'неизвестен'}</b></div>
            <div>Регистрация: ${dom.created_at || '?'}</div>
            <div>Регистратор: ${dom.registrar || '?'} <span style="color:var(--ink-400)">(${dom.registrar_risk || '?'})</span></div>
            <div>TLD риск: ${dom.tld_risk || '?'}</div>
            <div>WHOIS скрыт: ${dom.whois_privacy ? '<span style="color:var(--orange)">Да</span>' : 'Нет'}</div>
            <div>DNSSEC: ${dom.dnssec ? '<span style="color:var(--green)">Да</span>' : 'Нет'}</div>
          </div>
          <div>
            <h4 style="color:var(--blue-800);margin-bottom:8px">🖧 Инфраструктура</h4>
            <div>IP: <span class="mono">${(dns.ip || []).join(', ') || '?'}</span></div>
            <div>Страна: ${dns.country || '?'} · ${dns.city || ''}</div>
            <div>ASN: ${dns.asn_org || '?'}</div>
            <div>CDN: ${dns.cdn || 'Нет'} · Cloud: ${dns.cloud || '?'}</div>
            <div>MX: ${dns.mx_provider || 'custom'}</div>
            <div>Latency: ${dns.latency_ms ? dns.latency_ms + 'ms' : '?'}</div>
            <div>SPF: ${dns.spf ? '✓' : '✗'} · DMARC: ${dns.dmarc ? '✓' : '✗'}</div>
          </div>
          <div>
            <h4 style="color:var(--blue-800);margin-bottom:8px">🔒 SSL/TLS</h4>
            <div>SSL: ${ssl.has_ssl ? '<span style="color:var(--green)">Да</span>' : '<span style="color:var(--red)">Нет</span>'}</div>
            ${ssl.has_ssl ? `
              <div>Издатель: ${ssl.issuer || '?'} (${ssl.cert_type || '?'})</div>
              <div>Действует до: ${ssl.valid_to || '?'}</div>
              <div>TLS: ${(ssl.tls || []).join(', ') || '?'}</div>
              <div>SAN: ${ssl.san_count || 0} доменов</div>
              <div>crt.sh: ${ssl.ct_certs || 0} сертификатов, ${ssl.ct_subdomains || 0} субдоменов</div>
            ` : ''}
          </div>
          <div>
            <h4 style="color:var(--blue-800);margin-bottom:8px">🛡 Безопасность</h4>
            <div>Spamhaus: ${sec.spamhaus ? '<span style="color:var(--red)">В списке!</span>' : '<span style="color:var(--green)">Чисто</span>'}</div>
            <div>Security headers: ${sec.headers_count || 0}/6</div>
            ${(sec.headers_missing || []).length ? '<div style="color:var(--ink-400);font-size:13px">Нет: ' + sec.headers_missing.join(', ') + '</div>' : ''}
          </div>
          <div>
            <h4 style="color:var(--blue-800);margin-bottom:8px">⚖ Юридика</h4>
            <div>ToS: ${leg.tos ? '<span style="color:var(--green)">Есть</span>' : '<span style="color:var(--red)">Нет</span>'} · Privacy: ${leg.privacy ? '<span style="color:var(--green)">Есть</span>' : '<span style="color:var(--red)">Нет</span>'}</div>
            <div>Компания: ${leg.company || 'Не найдена'}</div>
            <div>Рег. номер: ${leg.reg_number || 'Нет'}</div>
            <div>Юрисдикция: ${leg.jurisdiction || '?'}</div>
            <div>Email: ${leg.email || '—'}</div>
            <div>Телефон: ${leg.phone || '—'}</div>
            ${(leg.social || []).length ? '<div>Соцсети: ' + leg.social.join(', ') + '</div>' : ''}
          </div>
          <div>
            <h4 style="color:var(--blue-800);margin-bottom:8px">⚙ Технологии</h4>
            <div>CMS: ${tech.cms || '—'}</div>
            <div>Framework: ${tech.framework || '—'}</div>
            ${(tech.analytics || []).length ? '<div>Analytics: ' + tech.analytics.join(', ') + '</div>' : ''}
            ${(tech.payments || []).length ? '<div>Платежи: ' + tech.payments.join(', ') + '</div>' : ''}
            ${tech.chat ? '<div>Чат: ' + tech.chat + '</div>' : ''}
          </div>
        </div>
        <div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--ink-200);color:var(--ink-400);font-size:13px;text-align:center">
          Проверено за ${Math.round(data.duration_ms / 1000)} сек · ${new Date().toLocaleString('ru-RU')}
        </div>
      </div>
    `;
  }

  document.querySelectorAll('.scan-form').forEach(handleScanSubmit);

  // ===== "Полный отчёт" button — scroll to details =====
  let _lastScanData = null;
  const origRenderResult = renderResult;
  renderResult = function(data) {
    _lastScanData = data;
    origRenderResult(data);
  };

  document.getElementById('fullReportBtn')?.addEventListener('click', (e) => {
    e.preventDefault();
    const det = document.getElementById('scanDetails');
    if (det) {
      det.scrollIntoView({behavior: 'smooth', block: 'start'});
    } else if (_lastScanData) {
      renderDetails(_lastScanData);
      setTimeout(() => {
        document.getElementById('scanDetails')?.scrollIntoView({behavior:'smooth', block:'start'});
      }, 100);
    } else {
      alert('Сначала проверьте домен — введите URL и нажмите «Проверить»');
    }
  });

  // ===== AUTH SYSTEM =====
  var _authToken = localStorage.getItem('ds_token') || null;
  var _authUser = JSON.parse(localStorage.getItem('ds_user') || 'null');

  function updateAuthUI() {
    var loginBtn = document.querySelector('.btn-ghost');
    if (!loginBtn) return;
    if (_authToken && _authUser) {
      loginBtn.textContent = _authUser.name || 'Account';
      loginBtn.onclick = function(e) { e.preventDefault(); showAccountModal(); };
    } else {
      loginBtn.textContent = 'Войти';
      loginBtn.onclick = function(e) { e.preventDefault(); showAuthModal(); };
    }
  }

  function showAuthModal() {
    var existing = document.getElementById('authModal');
    if (existing) existing.remove();
    var m = document.createElement('div');
    m.id = 'authModal';
    m.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);backdrop-filter:blur(4px);z-index:9998;display:flex;align-items:center;justify-content:center';
    m.innerHTML = '<div style="background:#fff;border-radius:16px;padding:32px;width:400px;max-width:90vw;box-shadow:0 20px 60px rgba(0,0,0,0.15)">'
      + '<h3 style="margin:0 0 20px;font-size:22px;color:#0F172A">Войти в DomainScan</h3>'
      + '<div id="authTabs" style="display:flex;gap:0;margin-bottom:20px;border-radius:8px;overflow:hidden;border:1px solid #E2E8F0">'
      + '<button id="tabLogin" style="flex:1;padding:8px;border:none;background:#1E40AF;color:#fff;font-weight:600;cursor:pointer" onclick="switchTab(\'login\')">Вход</button>'
      + '<button id="tabRegister" style="flex:1;padding:8px;border:none;background:#F1F5F9;color:#64748B;font-weight:600;cursor:pointer" onclick="switchTab(\'register\')">Регистрация</button>'
      + '</div>'
      + '<div id="authForm">'
      + '<input id="authName" type="text" placeholder="Имя" style="display:none;width:100%;padding:12px;border:1px solid #E2E8F0;border-radius:8px;margin-bottom:12px;font-size:15px;box-sizing:border-box">'
      + '<input id="authEmail" type="email" placeholder="Email" style="width:100%;padding:12px;border:1px solid #E2E8F0;border-radius:8px;margin-bottom:12px;font-size:15px;box-sizing:border-box">'
      + '<input id="authPass" type="password" placeholder="Пароль (мин. 6 символов)" style="width:100%;padding:12px;border:1px solid #E2E8F0;border-radius:8px;margin-bottom:16px;font-size:15px;box-sizing:border-box">'
      + '<div id="authError" style="color:#EF4444;font-size:13px;margin-bottom:12px;display:none"></div>'
      + '<button id="authSubmit" style="width:100%;padding:12px;background:#1E40AF;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer">Войти</button>'
      + '</div>'
      + '<button style="position:absolute;top:12px;right:16px;background:none;border:none;font-size:24px;color:#94A3B8;cursor:pointer" onclick="this.closest(\'#authModal\').remove()">x</button>'
      + '</div>';
    document.body.appendChild(m);
    m.addEventListener('click', function(e) { if (e.target === m) m.remove(); });
    document.getElementById('authSubmit').addEventListener('click', doAuth);
    document.getElementById('authPass').addEventListener('keydown', function(e) { if (e.key === 'Enter') doAuth(); });
    window._authMode = 'login';
  }

  window.switchTab = function(mode) {
    window._authMode = mode;
    var tabL = document.getElementById('tabLogin');
    var tabR = document.getElementById('tabRegister');
    var nameF = document.getElementById('authName');
    var btn = document.getElementById('authSubmit');
    if (mode === 'register') {
      tabR.style.background = '#1E40AF'; tabR.style.color = '#fff';
      tabL.style.background = '#F1F5F9'; tabL.style.color = '#64748B';
      nameF.style.display = 'block';
      btn.textContent = 'Зарегистрироваться';
    } else {
      tabL.style.background = '#1E40AF'; tabL.style.color = '#fff';
      tabR.style.background = '#F1F5F9'; tabR.style.color = '#64748B';
      nameF.style.display = 'none';
      btn.textContent = 'Войти';
    }
  };

  async function doAuth() {
    var email = document.getElementById('authEmail').value.trim();
    var pass = document.getElementById('authPass').value;
    var name = document.getElementById('authName').value.trim();
    var errEl = document.getElementById('authError');
    var btn = document.getElementById('authSubmit');
    errEl.style.display = 'none';

    if (!email || !pass) { errEl.textContent = 'Заполните все поля'; errEl.style.display = 'block'; return; }

    btn.disabled = true;
    btn.textContent = '...';

    try {
      var endpoint = window._authMode === 'register' ? '/api/auth/register' : '/api/auth/login';
      var body = window._authMode === 'register' ? {email: email, password: pass, name: name} : {email: email, password: pass};
      var resp = await fetch(endpoint, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
      var data = await resp.json();
      if (!resp.ok) { errEl.textContent = data.detail || 'Ошибка'; errEl.style.display = 'block'; btn.disabled = false; btn.textContent = window._authMode === 'register' ? 'Зарегистрироваться' : 'Войти'; return; }
      _authToken = data.token;
      _authUser = {name: data.name, email: data.email};
      localStorage.setItem('ds_token', _authToken);
      localStorage.setItem('ds_user', JSON.stringify(_authUser));
      updateAuthUI();
      document.getElementById('authModal').remove();
    } catch (e) {
      errEl.textContent = 'Ошибка сети'; errEl.style.display = 'block';
    }
    btn.disabled = false;
    btn.textContent = window._authMode === 'register' ? 'Зарегистрироваться' : 'Войти';
  }

  function showAccountModal() {
    var existing = document.getElementById('authModal');
    if (existing) existing.remove();
    var m = document.createElement('div');
    m.id = 'authModal';
    m.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);backdrop-filter:blur(4px);z-index:9998;display:flex;align-items:center;justify-content:center';

    var historyHtml = '';
    if (_authUser) {
      // Fetch history
      fetch('/api/auth/me', {headers: {'Authorization': 'Bearer ' + _authToken}})
        .then(function(r) { return r.json(); })
        .then(function(d) {
          var hEl = document.getElementById('historyList');
          if (hEl && d.history) {
            hEl.innerHTML = d.history.reverse().map(function(h) {
              var color = h.level === 'danger' ? '#EF4444' : h.level === 'high_risk' ? '#F97316' : h.level === 'caution' ? '#EAB308' : '#22C55E';
              return '<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #F1F5F9">'
                + '<span style="font-weight:500">' + h.domain + '</span>'
                + '<span style="color:' + color + ';font-weight:700">' + h.score + '/100</span>'
                + '</div>';
            }).join('');
          }
        }).catch(function() {});
    }

    m.innerHTML = '<div style="background:#fff;border-radius:16px;padding:32px;width:440px;max-width:90vw;box-shadow:0 20px 60px rgba(0,0,0,0.15);position:relative">'
      + '<h3 style="margin:0 0 4px;font-size:22px;color:#0F172A">' + (_authUser ? _authUser.name : '') + '</h3>'
      + '<p style="color:#64748B;font-size:14px;margin:0 0 20px">' + (_authUser ? _authUser.email : '') + '</p>'
      + '<h4 style="margin:0 0 12px;font-size:16px;color:#1E40AF">История проверок</h4>'
      + '<div id="historyList" style="max-height:300px;overflow-y:auto;margin-bottom:20px"><div style="color:#94A3B8;font-size:14px">Загрузка...</div></div>'
      + '<button onclick="_authToken=null;_authUser=null;localStorage.removeItem(\'ds_token\');localStorage.removeItem(\'ds_user\');updateAuthUI();this.closest(\'#authModal\').remove()" style="width:100%;padding:10px;background:#F1F5F9;color:#64748B;border:none;border-radius:8px;font-size:14px;cursor:pointer">Выйти</button>'
      + '<button style="position:absolute;top:12px;right:16px;background:none;border:none;font-size:24px;color:#94A3B8;cursor:pointer" onclick="this.closest(\'#authModal\').remove()">x</button>'
      + '</div>';
    document.body.appendChild(m);
    m.addEventListener('click', function(e) { if (e.target === m) m.remove(); });
  }

  // Initialize auth UI
  updateAuthUI();

  // ===== SCAN LOADING SCREEN =====
  function showScanGame(domain) {
    var cleaned = domain.replace(/^https?:\/\//, '').replace(/\/.*$/, '').toLowerCase();
    var el = document.createElement('div');
    el.id = 'scanOverlay';
    el.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:#08090b;z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:Inter,sans-serif;color:#fff';

    var style = document.createElement('style');
    style.textContent = '#scanOverlay .so-shield{font-size:48px;animation:soPulse 2s ease-in-out infinite;margin-bottom:20px}@keyframes soPulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.15);opacity:.7}}#scanOverlay .so-domain{font-size:20px;font-weight:700;color:#93C5FD;margin-bottom:24px;font-family:monospace}#scanOverlay .so-bar-wrap{width:320px;height:6px;background:rgba(59,130,246,0.15);border-radius:3px;overflow:hidden;margin-bottom:16px}#scanOverlay .so-bar{height:100%;background:linear-gradient(90deg,#3B82F6,#60A5FA);border-radius:3px;transition:width 0.8s ease}#scanOverlay .so-step{font-size:15px;color:#94A3B8;margin-bottom:8px}#scanOverlay .so-pct{font-size:13px;color:#475569;margin-top:8px;font-family:monospace}#scanOverlay .so-checks{margin-top:20px;display:flex;flex-wrap:wrap;gap:8px;max-width:340px;justify-content:center}#scanOverlay .so-chip{padding:4px 10px;border-radius:12px;font-size:11px;background:rgba(59,130,246,0.1);color:#60A5FA;border:1px solid rgba(59,130,246,0.15);transition:all .3s}#scanOverlay .so-chip.done{background:rgba(34,197,94,0.1);color:#22C55E;border-color:rgba(34,197,94,0.2)}';
    el.appendChild(style);

    var shield = document.createElement('div');
    shield.className = 'so-shield';
    shield.textContent = '\u{1F6E1}';
    el.appendChild(shield);

    var domEl = document.createElement('div');
    domEl.className = 'so-domain';
    domEl.textContent = cleaned;
    el.appendChild(domEl);

    var barWrap = document.createElement('div');
    barWrap.className = 'so-bar-wrap';
    var bar = document.createElement('div');
    bar.className = 'so-bar';
    bar.style.width = '0%';
    barWrap.appendChild(bar);
    el.appendChild(barWrap);

    var stepEl = document.createElement('div');
    stepEl.className = 'so-step';
    stepEl.textContent = '\u{1F310} Подключение...';
    el.appendChild(stepEl);

    var pctEl = document.createElement('div');
    pctEl.className = 'so-pct';
    pctEl.textContent = '0%';
    el.appendChild(pctEl);

    var checksDiv = document.createElement('div');
    checksDiv.className = 'so-checks';
    var chipNames = ['RDAP','DNS','SSL','Blacklists','Legal','Tech','Wayback','Headers','Score'];
    var chips = [];
    chipNames.forEach(function(n) {
      var chip = document.createElement('span');
      chip.className = 'so-chip';
      chip.textContent = n;
      checksDiv.appendChild(chip);
      chips.push(chip);
    });
    el.appendChild(checksDiv);

    document.body.appendChild(el);

    var steps = [
      ['\u{1F310}','Подключение к RDAP...',5],
      ['\u{1F4E1}','Проверка DNS записей...',12],
      ['\u{1F512}','SSL handshake...',20],
      ['\u{1F4DC}','Анализ сертификата...',28],
      ['\u{1F6E1}','Проверка чёрных списков...',38],
      ['\u{1F4C4}','Поиск ToS и Privacy Policy...',48],
      ['\u2699','Определение технологий...',58],
      ['\u{1F4CA}','Анализ аналитики...',65],
      ['\u{1F550}','Запрос Wayback Machine...',75],
      ['\u{1F510}','Проверка security headers...',85],
      ['\u{1F4C8}','Вычисление Trust Score...',95]
    ];
    var idx = 0, running = true;
    var iv = setInterval(function() {
      if (!running || idx >= steps.length) return;
      var s = steps[idx];
      bar.style.width = s[2] + '%';
      stepEl.textContent = s[0] + ' ' + s[1];
      pctEl.textContent = s[2] + '%';
      if (idx < chips.length) chips[idx].classList.add('done');
      idx++;
    }, 2200);

    return {
      stop: function() {
        running = false;
        clearInterval(iv);
        bar.style.width = '100%';
        pctEl.textContent = '100%';
        stepEl.textContent = '\u2705 Готово!';
        chips.forEach(function(c) { c.classList.add('done'); });
        setTimeout(function() {
          el.style.transition = 'opacity .4s';
          el.style.opacity = '0';
          setTimeout(function() { el.remove(); }, 400);
        }, 600);
      }
    };
  }

  // ===== TWEAKS =====
  const tweaks = document.getElementById('tweaks');
  const defaultsEl = document.getElementById('tweak-defaults');
  let tweakState = defaultsEl ? JSON.parse(defaultsEl.textContent) : {accent:'#1E40AF', anims:true};

  const applyAccent = (c) => {
    document.documentElement.style.setProperty('--accent', c);
    document.documentElement.style.setProperty('--blue-800', c);
  };
  const applyAnims = (on) => {
    document.documentElement.style.setProperty('--anim', on ? 'running' : 'paused');
    document.documentElement.classList.toggle('no-anim', !on);
  };
  applyAccent(tweakState.accent);
  applyAnims(tweakState.anims);

  const persist = (patch) => {
    tweakState = {...tweakState, ...patch};
    window.parent.postMessage({type:'__edit_mode_set_keys', edits: patch}, '*');
  };

  window.addEventListener('message', (ev) => {
    if (!ev.data) return;
    if (ev.data.type === '__activate_edit_mode') tweaks?.classList.add('visible');
    else if (ev.data.type === '__deactivate_edit_mode') tweaks?.classList.remove('visible');
  });
  window.parent.postMessage({type:'__edit_mode_available'}, '*');

  document.getElementById('closeTweaks')?.addEventListener('click', () => {
    tweaks?.classList.remove('visible');
    window.parent.postMessage({type:'__edit_mode_dismissed'}, '*');
  });

  document.querySelectorAll('#accentSwatches .tw-swatch').forEach(sw => {
    sw.addEventListener('click', () => {
      document.querySelectorAll('#accentSwatches .tw-swatch').forEach(x => x.classList.remove('active'));
      sw.classList.add('active');
      applyAccent(sw.dataset.c);
      persist({accent: sw.dataset.c});
    });
  });

  const animBtn = document.getElementById('animBtn');
  animBtn?.addEventListener('click', () => {
    const on = !animBtn.classList.contains('active') ? true : false;
    animBtn.classList.toggle('active', on);
    animBtn.textContent = on ? 'включены' : 'выключены';
    applyAnims(on);
    persist({anims: on});
  });

  // mark active swatch matching current accent
  document.querySelectorAll('#accentSwatches .tw-swatch').forEach(sw => {
    sw.classList.toggle('active', sw.dataset.c.toLowerCase() === tweakState.accent.toLowerCase());
  });
})();
