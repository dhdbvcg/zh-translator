'use strict';

const $ = (id) => document.getElementById(id);
const API = "";   // 同源请求,由本地服务处理

function setStatus(state, text) {
  $("dot").className = "dot " + state;
  $("statusText").textContent = text;
}

async function api(path, options) {
  let res;
  try {
    res = await fetch(API + path, Object.assign({
      headers: { "Content-Type": "application/json" },
    }, options || {}));
  } catch (e) {
    // 网络层失败:服务没起、端口不通、被拦截。给出可执行的提示,
    // 而不是把浏览器原样的 "Failed to fetch" 抛给用户。
    throw new ApiError(
      "无法连接翻译服务,请确认已运行 zhtrans --serve --port " + (location.port || 8848),
      0,
      { offline: true }
    );
  }
  const data = await res.json().catch(function () {
    return { error: "响应不是合法 JSON" };
  });
  // 把 HTTP 状态码一并带出,便于自检区分「服务端错误」与「参数被拒」
  data._status = res.status;
  data._ok = res.ok;
  if (!res.ok) throw new ApiError(data.error || ("HTTP " + res.status), res.status, data);
  return data;
}

function ApiError(message, status, payload) {
  this.name = "ApiError";
  this.message = message;
  this.status = status;
  this.payload = payload || {};
}
ApiError.prototype = Object.create(Error.prototype);

// 覆盖大小语种,含若干低资源语言
const SAMPLES = [
  ['en', 'Hello world'],
  ['fr', 'Bonjour, comment allez-vous aujourd hui?'],
  ['de', 'Das Wetter ist heute sehr schön.'],
  ['ja', 'こんにちは、お元気ですか。'],
  ['ko', '안녕하세요, 오늘 어떻게 지내세요?'],
  ['ru', 'Привет, как дела сегодня?'],
  ['ar', 'مرحبا كيف حالك اليوم'],
  ['sw', 'Habari za asubuhi, hujambo?'],
  ['vi', 'Xin chào, bạn khỏe không?'],
  ['th', 'สวัสดีครับ สบายดีไหม'],
  ['km', 'ជំរាបសួរ តើអ្នកយុត្តទេ?'],
  ['ne', 'नमस्ते, तपाईं कसो हुनुहुन्छ?'],
  ['my', 'မင်္ဂလာပါ မင်္ဂလာပါ'],
  ['zu', 'Sawubona, unjani?'],
];

const BATCH_SAMPLE = [
  'Hello world',
  'Guten Tag',
  'Bonjour',
  'Спасибо большое',
  'ありがとう',
  'ሰላም',
].join('\n');

let lastResult = null;
async function doTranslate() {
  const text = $("input").value.trim();
  if (!text) { $("output").value = ''; return; }

  const payload = {
    text: text,
    from: $("srcLang").value,
    to: $("dstLang").value,
    speed: $("speed").value,
  };
  // beam 留空时交给服务端按速度档位自适应
  const beam = parseInt($("beam").value, 10);
  if (beam) payload.beam = beam;

  if ($("glossaryOn").checked) {
    try {
      payload.glossary = JSON.parse($("glossary").value || '{}');
    } catch (e) {
      $("timing").textContent = '术语表 JSON 格式错误';
      return;
    }
  }

  const t0 = performance.now();
  setStatus('busy', '翻译中…');
  try {
    const r = await api('/translate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    const ms = Math.round(performance.now() - t0);
    lastResult = r;
    $("output").value = r.translation;
    $("timing").textContent = ms + ' ms';

    let meta = r.source_lang + '  ';
    if (r.detected) meta += '自动识别  ';
    if (r.skipped) meta += '已跳过(源文本为中文)';
    $("detectMeta").textContent = meta;
    setStatus('ok', '就绪');
  } catch (e) {
    $("output").value = '错误:' + e.message;
    $("timing").textContent = '';
    setStatus('err', '请求失败');
  }
}

async function doBatch() {
  const lines = $("batchInput").value
    .split(/\r?\n/)
    .map(function (s) { return s.trim(); })
    .filter(Boolean);

  const out = $("batchOut");
  if (!lines.length) { out.innerHTML = ''; return; }

  out.innerHTML = '';
  setStatus('busy', '批量翻译中…');
  const t0 = performance.now();
  try {
    const r = await api('/batch', {
      method: 'POST',
      body: JSON.stringify({ texts: lines, from: 'auto' }),
    });
    const ms = Math.round(performance.now() - t0);
    out.innerHTML = '';

    r.translations.forEach(function (t, i) {
      const row = document.createElement("div");
      row.className = "batch-row";
      const left = document.createElement("div");
      left.className = "src";
      left.textContent = t.source_lang;
      const right = document.createElement("div");
      right.className = "dst";
      right.textContent = t.translation;
      if (t.skipped) {
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = '跳过';
        right.appendChild(tag);
      }
      row.appendChild(left);
      row.appendChild(right);
      out.appendChild(row);
      void i;
    });

    const sum = document.createElement("div");
    sum.className = "io-meta";
    sum.style.marginTop = '6px';
    sum.textContent = lines.length + ' 条 / ' + ms + ' ms';
    out.appendChild(sum);
    setStatus('ok', '就绪');
  } catch (e) {
    out.innerHTML = '';
    const err = document.createElement("div");
    err.className = "test-item fail";
    err.textContent = '批量失败: ' + e.message;
    out.appendChild(err);
    setStatus('err', '批量失败');
  }
}
function ms(start) { return Math.round(performance.now() - start); }

function assert(cond, msg) {
  if (!cond) throw new Error(msg || '断言失败');
}

function assertZh(s) {
  assert(typeof s === 'string', '译文不是字符串');
  assert(s.length > 0, '译文为空');
  return /[\u4e00-\u9fff]/.test(s);
}

function post(text, from, to) {
  const body = { text: text, from: from };
  if (to) body.to = to;
  return api('/translate', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

function renderTestItem(id, state, detail, cost) {
  const el = $("testList").querySelector('[data-id=' + JSON.stringify(id) + ']');
  if (!el) return;
  el.className = "test-item " + state;
  const mark = el.querySelector('.mark').textContent;
  el.querySelector('.mark').textContent =
    state === 'pass' ? '✓' :
    state === 'fail' ? '✗' : '·';
  void mark;
  el.querySelector('.detail').textContent = detail;
  el.querySelector('.ms').textContent =
    cost == null ? '' : cost + ' ms';
}

const TEST_DEFS = [
  { id: "health", name: "GET /health" },
  { id: "langs", name: "GET /langs" },
  { id: "en", name: "POST /translate en" },
  { id: "auto", name: "POST /translate auto" },
  { id: "hant", name: "POST /translate zh-Hant" },
  { id: "empty", name: "POST /translate 空文本" },
  { id: "bad", name: "POST /translate 非法语种" },
  { id: "batch", name: "POST /batch 混合语种" },
];

function buildTestList() {
  const box = $("testList");
  box.innerHTML = '';
  TEST_DEFS.forEach(function (t) {
    const el = document.createElement("div");
    el.className = "test-item";
    el.setAttribute("data-id", t.id);
    el.innerHTML =
      '<div class=\"mark\">·</div>' +
      '<div class=\"name\"></div>' +
      '<div class=\"detail\">待运行</div>' +
      '<div class=\"ms\"></div>';
    el.querySelector('.name').textContent = t.name;
    box.appendChild(el);
  });
}
async function runSelfTest() {
  $("btnSelfTest").disabled = true;
  buildTestList();
  const summary = $("testSummary");
  summary.innerHTML = '<span class=\"muted\">运行中…</span>';
  let passed = 0;
  let failed = 0;
  let aborted = false;

  const run = async function (id, fn) {
    renderTestItem(id, 'run', '运行中…', null);
    const t0 = performance.now();
    try {
      const detail = await fn();
      renderTestItem(id, 'pass', detail, ms(t0));
      passed += 1;
    } catch (e) {
      renderTestItem(id, 'fail', e.message, ms(t0));
      failed += 1;
      // 服务不可达时后续用例必然同样失败,记录后提前中止
      if (e.status === 0) aborted = true;
    }
  };

  await run("health", async function () {
    const r = await api('/health');
    assert(r.ok === true, 'ok 不为 true');
    return 'device=' + r.device + ', loaded=' + r.loaded;
  });

  // 服务连不上时继续跑完 8 项只会得到一串 Failed to fetch,掩盖真正原因。
  if (aborted) {
    TEST_DEFS.forEach(function (t) {
      if (t.id !== 'health') renderTestItem(t.id, 'fail', '未执行', null);
    });
    summary.className = 'test-summary';
    summary.innerHTML = '<span class="err">翻译服务未运行,无法测试。'
      + '请先执行 zhtrans --serve --port ' + (location.port || 8848)
      + ' ,并保持该窗口开启。</span>';
    $('btnSelfTest').disabled = false;
    setStatus('err', '服务未运行');
    return;
  }

  await run("langs", async function () {
    const r = await api('/langs');
    assert(r.count > 50, '语种数过少: ' + r.count);
    renderLangs(r.languages);
    return r.count + ' 种语言';
  });

  await run("en", async function () {
    const r = await post("Hello world", "en");
    assertZh(r.translation);
    return JSON.stringify(r.translation);
  });

  await run("auto", async function () {
    const r = await post("Das Wetter ist heute schön.", "auto");
    assert(r.detected === true, 'detected 应为 true');
    assert(r.source_lang.indexOf('deu') === 0,
      '德语识别为 ' + r.source_lang);
    assertZh(r.translation);
    return r.source_lang + '  ' + JSON.stringify(r.translation);
  });

  await run("hant", async function () {
    const r = await post("Hello world", "en", "zh-Hant");
    assertZh(r.translation);
    // 繁体通道应产出繁体字(与简体不同)
    return JSON.stringify(r.translation);
  });

  await run("empty", async function () {
    const r = await post("   ", "en");
    assert(r.skipped === true, '空文本应被跳过');
    return 'skipped=true,无异常';
  });

  await run("bad", async function () {
    // 非法语种应被服务端拒绝(4xx),而不是 500
    try {
      await post("hello", "不存在的语种");
    } catch (e) {
      assert(e.status === 400, '应为 400,实际 ' + e.status);
      assert(/不支持的语种/.test(e.message), '错误信息不符: ' + e.message);
      return '正确拒绝(400):' + e.message.slice(0, 24);
    }
    throw new Error('非法语种未被拒绝');
  });
  await run("batch", async function () {
    const r = await api('/batch', {
      method: 'POST',
      body: JSON.stringify({
        texts: ['Hello world', 'Guten Tag', 'Bonjour'],
        from: 'auto',
      }),
    });
    assert(r.translations.length === 3, '返回条数不符');
    r.translations.forEach(function (t) { assertZh(t.translation); });
    const langs = r.translations.map(function (t) { return t.source_lang; });
    assert(langs.indexOf('eng_Latn') !== -1, '未识别出英语');
    assert(langs.indexOf('deu_Latn') !== -1, '未识别出德语');
    assert(langs.indexOf('fra_Latn') !== -1, '未识别出法语');
    return langs.join(', ');
  });

  const cls = failed ? 'err' : 'ok';
  summary.className = 'test-summary';
  let msg = '通过 ' + passed + ' / ' + (passed + failed) + ' 项';
  if (failed) msg += '，失败 ' + failed + ' 项';
  summary.innerHTML = '<span class="' + cls + '">' + msg + '</span>';
  $('btnSelfTest').disabled = false;
  setStatus(failed ? 'err' : 'ok',
    failed ? '自检有失败项' : '全部通过');
}

// ---------------- 语种表 ----------------

let ALL_LANGS = [];
const TIER_MARK = { high: '★', mid: '☆', low: '·' };

function renderLangs(list) {
  ALL_LANGS = list || [];
  fillLangSelect();
  filterLangs();
}

function fillLangSelect() {
  const sel = $('srcLang');
  const current = sel.value;
  sel.innerHTML = '';
  const first = document.createElement('option');
  first.value = 'auto';
  first.textContent = '自动识别';
  sel.appendChild(first);
  ALL_LANGS.forEach(function (l) {
    const o = document.createElement('option');
    o.value = l.iso1;
    o.textContent = l.zh_name + ' (' + l.iso1 + ')';
    sel.appendChild(o);
  });
  sel.value = current || 'auto';
}

function filterLangs() {
  const q = $('langSearch').value.trim().toLowerCase();
  const tier = $('langFilter').value;
  const grid = $('langGrid');
  grid.innerHTML = '';
  let shown = 0;
  ALL_LANGS.forEach(function (l) {
    if (tier !== 'all' && l.resource_tier !== tier) return;
    if (q) {
      const hay = [l.zh_name, l.en_name, l.iso1, l.family].join(' ').toLowerCase();
      if (hay.indexOf(q) === -1) return;
    }
    const el = document.createElement('div');
    el.className = 'lang-item t-' + l.resource_tier;
    el.innerHTML = "<span class='code'></span><span class=\"name\"></span><span class='tier'></span>";
    el.querySelector('.code').textContent = l.iso1;
    el.querySelector('.name').textContent = l.zh_name;
    el.querySelector('.tier').textContent = TIER_MARK[l.resource_tier] || '';
    el.title = l.en_name + ' · ' + l.family + ' · ' + l.script;
    el.style.cursor = 'pointer';
    el.addEventListener('click', function () {
      $('srcLang').value = l.iso1;
      $('input').focus();
    });
    grid.appendChild(el);
    shown += 1;
  });
  $('langCount').textContent = shown + ' / ' + ALL_LANGS.length;
}
// ---------------- 初始化 ----------------

function buildSamples() {
  const box = $('samples');
  box.innerHTML = '';
  SAMPLES.forEach(function (s) {
    const b = document.createElement('button');
    b.className = 'chip';
    b.type = 'button';
    b.textContent = s[1].slice(0, 14);
    b.title = s[1];
    b.addEventListener('click', function () {
      $('input').value = s[1];
      $('srcLang').value = s[0];
      doTranslate();
    });
    box.appendChild(b);
  });
}

function wire() {
  const input = $('input');
  let timer = null;
  input.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(doTranslate, 500);
  });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      clearTimeout(timer);
      doTranslate();
    }
  });
  $('srcLang').addEventListener('change', doTranslate);
  $('dstLang').addEventListener('change', doTranslate);
  $('speed').addEventListener('change', doTranslate);

  $('glossaryOn').addEventListener('change', function (e) {
    $('glossary').disabled = !e.target.checked;
  });

  $('btnSwap').addEventListener('click', function () {
    const out = $('output').value;
    if (!out) return;
    navigator.clipboard.writeText(out).then(function () {
      const b = $('btnSwap');
      const old = b.textContent;
      b.textContent = '已复制';
      setTimeout(function () { b.textContent = old; }, 1200);
    });
  });

  $('btnBatch').addEventListener('click', doBatch);
  $('btnFillBatch').addEventListener('click', function () {
    $('batchInput').value = BATCH_SAMPLE;
  });
  $('btnSelfTest').addEventListener('click', runSelfTest);
  $('btnLangs').addEventListener('click', async function () {
    setStatus('busy', '拉取语种表…');
    try {
      const r = await api('/langs');
      renderLangs(r.languages);
      setStatus('ok', '就绪');
    } catch (e) {
      setStatus('err', '拉取失败');
    }
  });

  $('langSearch').addEventListener('input', filterLangs);
  $('langFilter').addEventListener('change', filterLangs);
}

async function init() {
  buildSamples();
  wire();
  setStatus('busy', '连接服务…');
  try {
    const h = await api('/health');
    setStatus('ok', '已连接 · ' + (h.device || 'cpu'));
  } catch (e) {
    setStatus('err', '无法连接服务');
    return;
  }
  try {
    const r = await api('/langs');
    renderLangs(r.languages);
  } catch (e) {
    /* 语种表非关键,失败不阻断 */
  }
}

init();