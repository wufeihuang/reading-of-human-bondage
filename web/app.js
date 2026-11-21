/* ===== Of Human Bondage · 阅读器 ===== */
(function () {
  'use strict';

  var LS = {
    get: function (k, d) {
      try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); }
      catch (e) { return d; }
    },
    set: function (k, v) {
      try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {}
    }
  };

  var CH = window.CHAPTER || {};
  var KEY = 'ohb:' + (CH.id || 'x');

  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }

  /* ---------------- 设置 ---------------- */

  var DEFAULTS = { trans: 1, words: 1, sents: 1, notes: 1, craft: 1, split: 0, collapse: 0, openanno: 0 };
  var cfg = Object.assign({}, DEFAULTS, LS.get('ohb:cfg', {}));

  function applyCfg() {
    document.body.dataset.trans = cfg.trans ? 'on' : 'off';
    document.body.dataset.words = cfg.words ? 'on' : 'off';
    document.body.dataset.sents = cfg.sents ? 'on' : 'off';
    document.body.dataset.notes = cfg.notes ? 'on' : 'off';
    document.body.dataset.craft = cfg.craft ? 'on' : 'off';
    document.body.dataset.split = cfg.split ? 'on' : 'off';
    $$('details.notes:not(.answers), details.craft').forEach(function (d) {
      d.open = !cfg.collapse;
    });
    $$('details.anno').forEach(function (d) {
      d.open = !!cfg.openanno;
    });
    $$('.settings input[data-set]').forEach(function (i) {
      i.checked = !!cfg[i.dataset.set];
    });
  }

  $$('.settings input[data-set]').forEach(function (i) {
    i.addEventListener('change', function () {
      cfg[i.dataset.set] = i.checked ? 1 : 0;
      LS.set('ohb:cfg', cfg);
      applyCfg();
      if (i.dataset.set === 'split') syncCompanion(true);
    });
  });

  var setBtn = $('#setBtn'), settings = $('#settings');
  if (setBtn && settings) {
    setBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      settings.hidden = !settings.hidden;
      document.body.classList.toggle('settings-open', !settings.hidden);
    });
    document.addEventListener('click', function (e) {
      if (!settings.hidden && !settings.contains(e.target) && e.target !== setBtn) {
        settings.hidden = true;
        document.body.classList.remove('settings-open');
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') settings.hidden = true;
    });
  }

  /* ---------------- 主题 / 字号 ---------------- */

  var themeBtn = $('.tools .theme');
  function setTheme(t, remember) {
    document.documentElement.dataset.theme = t;
    if (themeBtn) themeBtn.textContent = t === 'dark' ? '☀' : '☾';
    if (remember) LS.set('ohb:theme', t);
  }
  if (themeBtn) themeBtn.addEventListener('click', function () {
    setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark', true);
  });

  var fs = LS.get('ohb:fs', 1);
  function applyFs() {
    fs = Math.min(1.32, Math.max(0.86, fs));
    document.documentElement.style.setProperty('--fs', String(fs));
    LS.set('ohb:fs', fs);
  }
  $$('[data-fs]').forEach(function (b) {
    b.addEventListener('click', function () {
      fs += (b.dataset.fs === '+' ? 0.06 : -0.06);
      applyFs();
    });
  });

  /* ---------------- 侧栏 ---------------- */

  var PANELS = { left: 1, right: 1 };
  try { PANELS = Object.assign(PANELS, LS.get('ohb:panels', {})); } catch (e) {}

  function applyPanels(persist) {
    document.body.classList.toggle('no-left', !PANELS.left);
    document.body.classList.toggle('no-right', !PANELS.right);
    if (persist !== false && window.innerWidth >= 1080) LS.set('ohb:panels', PANELS);
  }

  var hasLeft = !!$('#navLeft'), hasRight = !!$('#navRight');
  var forcedMobile = window.innerWidth < 1080;
  if (forcedMobile) { PANELS.left = 0; PANELS.right = 0; }
  if (!hasLeft) PANELS.left = 0;
  if (!hasRight) PANELS.right = 0;
  applyPanels(false);

  var tl = $('#toggleLeft'), tr = $('#toggleRight'), tr2 = $('#toggleRight2');
  if (tr && !hasRight) tr.style.display = 'none';
  $$('[data-close]').forEach(function (b) {
    b.addEventListener('click', function () {
      if (b.dataset.close === 'left') PANELS.left = 0; else PANELS.right = 0;
      applyPanels();
    });
  });

  var scrim = $('#scrim');
  if (scrim) scrim.addEventListener('click', function () {
    PANELS.left = 0; PANELS.right = 0; applyPanels();
    var st = $('#settings');
    if (st) { st.hidden = true; document.body.classList.remove('settings-open'); }
  });
  if (tl) tl.addEventListener('click', function () { PANELS.left = PANELS.left ? 0 : 1; applyPanels(); });
  if (tr) tr.addEventListener('click', function () { PANELS.right = PANELS.right ? 0 : 1; applyPanels(); });
  if (tr2) tr2.addEventListener('click', function () { PANELS.right = 0; applyPanels(); });

  document.addEventListener('keydown', function (e) {
    if (e.target.matches('input, textarea')) return;
    if (e.key === 'Escape') {
      PANELS.left = 0; PANELS.right = 0; applyPanels();
      var st = $('#settings');
      if (st) { st.hidden = true; document.body.classList.remove('settings-open'); }
    }
    if (e.key === 'e' || e.key === 'E') $$('details').forEach(function (d) { d.open = true; });
    if (e.key === 'q' || e.key === 'Q') $$('details').forEach(function (d) { d.open = false; });
  });

  // 移动端：点目录后收起右栏
  document.addEventListener('click', function (e) {
    var a = e.target.closest('.nav-right a, .nav-left a');
    if (!a) return;
    if (window.innerWidth < 1080) {
      PANELS.left = 0; PANELS.right = 0; applyPanels();
    }
  });

  /* ---------------- 阅读进度 ---------------- */

  var readbar = $('#readbar');
  function paintProgress() {
    if (!readbar) return;
    var h = document.documentElement.scrollHeight - window.innerHeight;
    readbar.style.width = (h > 0 ? Math.min(100, window.scrollY / h * 100) : 0) + '%';
  }

  /* ---------------- 目录高亮 ---------------- */

  var tocLinks = $$('.toc a');
  var targets = tocLinks.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); }).filter(Boolean);

  if ('IntersectionObserver' in window && targets.length) {
    var visible = {};
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { visible[en.target.id] = en.isIntersecting; });
      var current = null;
      for (var i = 0; i < targets.length; i++) {
        if (visible[targets[i].id]) { current = targets[i].id; break; }
      }
      if (current) {
        tocLinks.forEach(function (a) {
          a.classList.toggle('active', a.getAttribute('href') === '#' + current);
        });
      }
    }, { rootMargin: '-64px 0px -72% 0px', threshold: 0 });
    targets.forEach(function (t) { io.observe(t); });
  }

  /* ---------------- 段号跳转 ---------------- */

  function flash(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('flash');
    void el.offsetWidth;
    el.classList.add('flash');
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href^="#p-"]');
    if (!a) return;
    var id = a.getAttribute('href').slice(1);
    var el = document.getElementById(id);
    if (!el) return;
    e.preventDefault();
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    flash(id);
    history.replaceState(null, '', '#' + id);
  });
  if (location.hash && /^#p-/.test(location.hash)) setTimeout(function () { flash(location.hash.slice(1)); }, 300);

  /* ---------------- J / K 逐段 ---------------- */

  var units = $$('.unit');
  function currentUnit() {
    var best = 0, bestD = 1e9;
    units.forEach(function (u, i) {
      var d = Math.abs(u.getBoundingClientRect().top - 120);
      if (d < bestD) { bestD = d; best = i; }
    });
    return best;
  }
  function gotoUnit(i) {
    if (!units.length) return;
    i = Math.max(0, Math.min(units.length - 1, i));
    units.forEach(function (u) { u.classList.remove('focus'); });
    units[i].classList.add('focus');
    units[i].scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  document.addEventListener('keydown', function (e) {
    if (e.target.matches('input, textarea')) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === 'j' || e.key === 'J') { gotoUnit(currentUnit() + 1); }
    if (e.key === 'k' || e.key === 'K') { gotoUnit(currentUnit() - 1); }
  });

  /* ---------------- 朗读 ---------------- */

  if ('speechSynthesis' in window) {
    $$('.reader p, .en').forEach(function (p) {
      var btn = document.createElement('button');
      btn.className = 'speak';
      btn.type = 'button';
      btn.title = '朗读这一段';
      btn.textContent = '▶';
      btn.addEventListener('click', function (ev) {
        ev.stopPropagation();
        if (speechSynthesis.speaking) { speechSynthesis.cancel(); return; }
        var u = new SpeechSynthesisUtterance(p.innerText.replace('▶', ''));
        u.lang = 'en-GB';
        u.rate = 0.9;
        speechSynthesis.speak(u);
      });
      p.appendChild(btn);
    });
  }

  /* ---------------- 分屏讲解 ---------------- */

  var scenes = $$('.scene');
  var panes = $$('.companion .cp');
  var currentScene = null;

  function syncCompanion(force) {
    if (!scenes.length || !panes.length) return;
    if (document.body.dataset.split !== 'on') return;
    var active = null;
    for (var i = 0; i < scenes.length; i++) {
      var r = scenes[i].getBoundingClientRect();
      if (r.top <= 200) active = scenes[i].dataset.scene;
    }
    if (!active) active = scenes[0].dataset.scene;
    if (active !== currentScene || force) {
      currentScene = active;
      panes.forEach(function (p) { p.hidden = p.dataset.scene !== active; });
    }
  }

  /* ---------------- 打卡 ---------------- */

  var checks = $$('.check input');
  var bar = $('.bar i');
  var barText = $('.bar-label span:last-child');

  function loadChecks() {
    var saved = LS.get(KEY, {});
    checks.forEach(function (c) { c.checked = !!saved[c.dataset.k]; });
    paintChecks();
  }
  function paintChecks() {
    var done = checks.filter(function (c) { return c.checked; }).length;
    var pct = checks.length ? Math.round(done / checks.length * 100) : 0;
    if (bar) bar.style.width = pct + '%';
    if (barText) barText.textContent = done + ' / ' + checks.length;
  }
  checks.forEach(function (c) {
    c.addEventListener('change', function () {
      var saved = LS.get(KEY, {});
      saved[c.dataset.k] = c.checked;
      LS.set(KEY, saved);
      paintChecks();
    });
  });

  /* ---------------- 写作区 ---------------- */

  var ta = $('.writing textarea');
  if (ta) {
    var countEl = $('.writing .count');
    var statusEl = $('.writing .status');

    function count(text) {
      var en = (text.match(/[A-Za-z][A-Za-z'’\-]*/g) || []).length;
      var zh = (text.match(/[\u4e00-\u9fff]/g) || []).length;
      return en + zh;
    }
    ta.value = LS.get(KEY + ':writing', '');
    var t;
    function upd() {
      if (countEl) countEl.textContent = count(ta.value) + ' 词';
      clearTimeout(t);
      t = setTimeout(function () {
        LS.set(KEY + ':writing', ta.value);
        if (statusEl) { statusEl.textContent = '已保存'; setTimeout(function () { statusEl.textContent = ''; }, 1500); }
      }, 600);
    }
    ta.addEventListener('input', upd);
    upd();

    var copyBtn = $('.writing .copy');
    if (copyBtn) copyBtn.addEventListener('click', function () {
      ta.select(); document.execCommand('copy');
      if (statusEl) statusEl.textContent = '已复制';
    });
    var clearBtn = $('.writing .clear');
    if (clearBtn) clearBtn.addEventListener('click', function () {
      if (!confirm('清空这段练习？')) return;
      ta.value = ''; upd();
    });
  }

  /* ---------------- 生词本 ---------------- */

  var WB_KEY = 'ohb:words';

  function wbAll() { return LS.get(WB_KEY, []); }
  function wbKey(ch, pid, w) { return ch + '|' + pid + '|' + w; }

  function paintWbCount() {
    var n = wbAll().length;
    var c = $('#wbCount');
    if (c) c.textContent = n;
  }

  function markSaved() {
    var set = {};
    wbAll().forEach(function (x) { set[wbKey(x.ch, x.pid, x.w)] = 1; });
    $$('.gloss').forEach(function (g) {
      var unit = g.closest('.unit');
      var pid = unit ? unit.id : '';
      g.classList.toggle('saved', !!set[wbKey(CH.id, pid, g.textContent)]);
    });
  }

  function toast(msg) {
    var el = $('#toast');
    if (!el) return;
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.classList.remove('show'); }, 1500);
  }

  document.addEventListener('click', function (e) {
    var g = e.target.closest('.gloss');
    if (!g) return;
    var unit = g.closest('.unit');
    var pid = unit ? unit.id : '';
    var w = g.textContent;
    var tip = g.dataset.tip || '';
    var list = wbAll();
    var k = wbKey(CH.id, pid, w);
    var idx = list.findIndex(function (x) { return wbKey(x.ch, x.pid, x.w) === k; });
    if (idx > -1) {
      list.splice(idx, 1);
      LS.set(WB_KEY, list);
      g.classList.remove('saved');
      toast('已移出生词本');
    } else {
      list.push({ w: w, tip: tip, ch: CH.id, href: CH.href, pid: pid, n: (CH.num || '') });
      LS.set(WB_KEY, list);
      g.classList.add('saved');
      toast('已加入生词本');
    }
    paintWbCount();
  });

  var wbBtn = $('#wbBtn');
  if (wbBtn) {
    wbBtn.addEventListener('click', function () {
      var list = wbAll();
      var html = '<h3>生词本</h3><p class="hint">在原文里点虚线词即可收进来；再点一次移出。</p>';
      if (!list.length) {
        html += '<div class="wb-empty">还是空的。读到不认识的词，点一下它。</div>';
      } else {
        html += '<div class="wb-list">';
        list.slice().sort(function (a, b) {
          return (a.n || '').localeCompare(b.n || '', 'zh-Hans-CN', { numeric: true });
        }).forEach(function (x) {
          var file = x.href || String(x.ch || '').replace(/^ch(\d)$/, 'ch0$1') + '.html';
          var href = x.pid ? (file + '#' + x.pid) : file;
          html += '<a class="wb-item" href="' + href + '"><b>' + esc(x.w) + '</b><span>' +
                  esc(x.tip) + '</span><em>' + esc(x.n || '') + '</em></a>';
        });
        html += '</div>';
      }
      html += '<div class="quiz-foot" style="margin-top:14px"><button class="btn" id="closeWb" type="button">关闭</button></div>';
      openSheet(html);
      var c = $('#closeWb');
      if (c) c.addEventListener('click', closeSheet);
    });
  }

  /* ---------------- 词汇小测 ---------------- */

  function cleanGloss(g) {
    var t = String(g || '').replace(/^[=＝]\s*/, '');
    t = t.split('（')[0].trim();
    return t.replace(/[；;]\s*$/, '');
  }

  var words = (CH.words || []).map(function (w) {
    return { w: w.w, g: cleanGloss(w.g) };
  }).filter(function (w) { return w.g && w.g.length >= 2 && /[\u4e00-\u9fff]/.test(w.g); });

  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; }
    return a;
  }

  function buildQuiz() {
    if (words.length < 5) return;
    var picked = shuffle(words.slice()).slice(0, Math.min(8, words.length));
    var html = '<h3>词义小测</h3><p class="hint">从本章词表里抽 8 个，选一个正确释义。</p>';
    picked.forEach(function (w) {
      var others = shuffle(words.filter(function (x) { return x.g !== w.g; })).slice(0, 3).map(function (x) { return x.g; });
      var opts = shuffle(others.concat([w.g]));
      html += '<div class="q" data-answer="' + esc(w.g) + '"><div class="w">' + esc(w.w) + '</div><div class="opts">';
      opts.forEach(function (o) { html += '<button class="opt" type="button">' + esc(o) + '</button>'; });
      html += '</div><div class="fb"></div></div>';
    });
    html += '<div class="quiz-foot"><span class="score"></span><button class="btn" id="closeQuiz" type="button">关闭</button></div>';
    openSheet(html);

    var total = picked.length, right = 0, answered = 0;
    $$('.sheet .q').forEach(function (q) {
      var ans = q.dataset.answer;
      $$('.opt', q).forEach(function (o) {
        if (o.textContent === ans) o.dataset.correct = '1';
        o.addEventListener('click', function () {
          if (q.dataset.done) return;
          q.dataset.done = '1';
          answered++;
          if (o.dataset.correct === '1') { right++; o.classList.add('right'); $('.fb', q).textContent = '对。'; }
          else {
            o.classList.add('wrong');
            $('.opt[data-correct="1"]', q).classList.add('right');
            $('.fb', q).textContent = '正确释义：' + ans;
          }
          var sc = $('.score');
          if (sc) sc.textContent = answered + ' / ' + total + ' · 答对 ' + right;
        });
      });
    });
    var c = $('#closeQuiz');
    if (c) c.addEventListener('click', closeSheet);
  }

  /* ---------------- 弹层 ---------------- */

  function openSheet(html) {
    var modal = $('#sheetModal');
    if (!modal) return;
    $('.sheet', modal).innerHTML = html;
    modal.classList.add('open');
  }
  function closeSheet() {
    var modal = $('#sheetModal');
    if (modal) modal.classList.remove('open');
  }

  var sheetModal = document.createElement('div');
  sheetModal.className = 'modal';
  sheetModal.id = 'sheetModal';
  sheetModal.innerHTML = '<div class="sheet"></div>';
  document.body.appendChild(sheetModal);
  sheetModal.addEventListener('click', function (e) { if (e.target === sheetModal) closeSheet(); });

  ['#quizBtn', '#quizBtn2'].forEach(function (sel) {
    var b = $(sel);
    if (b) b.addEventListener('click', buildQuiz);
  });

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  /* ---------------- 搜索（技法页） ---------------- */

  var search = $('.search');
  if (search) {
    search.addEventListener('input', function () {
      var q = search.value.trim().toLowerCase();
      $$('table.gen tr').forEach(function (tr) {
        if (tr.querySelector('th')) return;
        tr.style.display = (!q || tr.textContent.toLowerCase().indexOf(q) > -1) ? '' : 'none';
      });
      $$('.doc-main h2, .doc-main h3, .doc-main p').forEach(function (el) {
        el.style.display = (!q || el.textContent.toLowerCase().indexOf(q) > -1) ? '' : 'none';
      });
    });
  }

  /* ---------------- 首页进度 ---------------- */

  var cells = $$('.cell[data-ch]');
  cells.forEach(function (c) {
    var saved = LS.get('ohb:ch' + c.dataset.ch, {});
    var n = Object.keys(saved).filter(function (k) { return saved[k]; }).length;
    if (n >= 5) c.classList.add('done');
  });

  /* ---------------- 初始化 ---------------- */

  setTheme(LS.get('ohb:theme', 'light'), false);
  applyFs();
  applyCfg();
  loadChecks();
  paintWbCount();
  markSaved();

  if (document.body.dataset.split === 'on') syncCompanion(true);

  var raf = null;
  window.addEventListener('scroll', function () {
    paintProgress();
    if (raf) return;
    raf = requestAnimationFrame(function () {
      raf = null;
      syncCompanion(false);
    });
  }, { passive: true });
  paintProgress();
})();
