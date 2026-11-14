// 브라우저에서 도는 계산. recheck/read_raw.py 와 recheck/fit.py 를 같은 식, 같은 이름으로 옮긴 것이다.
// 두 벌이 같은 답을 내는지는 맨 아래 selfCheck 가 페이지를 열 때마다 비교한다.
"use strict";

// 절연막 용량 (F/cm²). fit.py 의 C_OX 와 같은 값 (가정, docs/설계.md 3절).
const C_OX = 1.75e-8;

// ── read_raw.py ──────────────────────────────────────────────

// 칸 하나를 숫자로 바꾼다. '*'나 빈칸처럼 숫자가 아니면 null.
function toNumber(cell) {
  return cell === "" || Number.isNaN(Number(cell)) ? null : Number(cell);
}

// 파일 글자에서 이름이 name 인 측정을 찾아 행 목록을 돌려준다. 행 하나는 {열 이름: 숫자 또는 null}.
// sep: 칸을 나누는 글자. CSV 는 쉼표, DAT 는 탭.
function readSection(text, sep, name) {
  let header = null, inside = false;
  const rows = [];
  for (const line of text.split(/\r?\n/)) {
    if (line.startsWith("DATA:")) {
      if (inside) break; // 다음 측정이 시작되면 끝
      inside = line.replace(/,/g, " ").trim().split(/\s+/)[1] === name;
      continue;
    }
    if (!inside) continue;
    const cells = line.split(sep).map((c) => c.trim());
    if (!cells.some((c) => c)) continue; // 빈 줄
    if (header === null) {
      header = cells.filter((c) => c);
      continue;
    }
    const row = {};
    header.forEach((h, k) => { row[h] = toNumber(cells[k] ?? ""); });
    rows.push(row);
  }
  if (header === null) throw new Error(`${name} 측정을 찾지 못했습니다`);
  return rows;
}

// MOBILITY 측정의 [전압, 전류] 목록. 파일의 순서와 부호 그대로.
function mobilityPoints(text, fileName) {
  const sep = fileName.toLowerCase().endsWith(".csv") ? "," : "\t";
  return readSection(text, sep, "MOBILITY").map((row, n) => {
    // 못 읽은 숫자를 건너뛰거나 채우지 않는다. 멈추고 알린다.
    if (row.VD == null || row.ID == null) throw new Error(`MOBILITY ${n + 1}번째 줄의 VD 또는 ID를 읽지 못했습니다`);
    return [row.VD, row.ID];
  });
}

// ── fit.py ───────────────────────────────────────────────────

const sum = (list) => list.reduce((total, x) => total + x, 0);

// 점들에 가장 잘 맞는 직선 y = a·x + b (최소제곱법). 돌려주는 값: [기울기 a, 절편 b, R²].
function lineFit(xs, ys) {
  const n = xs.length;
  const meanX = sum(xs) / n, meanY = sum(ys) / n;
  const sxx = sum(xs.map((x) => (x - meanX) ** 2));
  const sxy = sum(xs.map((x, k) => (x - meanX) * (ys[k] - meanY)));
  const syy = sum(ys.map((y) => (y - meanY) ** 2));
  const a = sxy / sxx;
  const b = meanY - a * meanX;
  const r2 = syy ? (sxy * sxy) / (sxx * syy) : 1.0;
  return [a, b, r2];
}

// 측정 범위를 0 V에서부터 width V씩 겹치지 않게 나눈 구간 목록. 음의 전압으로 켜지는 소자는 0~−2, −2~−4, …
function windows(points, width = 2) {
  const end = points.map(([v]) => v).reduce((far, v) => (Math.abs(v) > Math.abs(far) ? v : far));
  const sign = end > 0 ? 1 : -1;
  const count = Math.floor(Math.abs(end) / width + 1e-9);
  return Array.from({ length: count }, (_, k) => [sign * k * width, sign * (k + 1) * width]);
}

// 구동 방향으로 √|I|가 커지는 구간인가. 아니면 이동도를 계산하지 않는다.
function turnedOn(r) {
  return r.slope * (r.v_from + r.v_to) > 0;
}

// 그 구간에서 나온 문턱전압이 구간 시작점보다 앞에 있는가.
function vthBeforeWindow(r) {
  const sign = r.v_from + r.v_to > 0 ? 1 : -1;
  return turnedOn(r) && sign * r.vth <= Math.min(sign * r.v_from, sign * r.v_to) + 1e-9;
}

// 전압이 vFrom 과 vTo 사이(양끝 포함)인 점들로 μ와 Vth를 구한다. 점이 3개보다 적으면 null.
function saturationFit(points, w, l, vFrom, vTo) {
  const lo = Math.min(vFrom, vTo) - 1e-9, hi = Math.max(vFrom, vTo) + 1e-9;
  const chosen = points.filter(([v]) => lo <= v && v <= hi).map(([v, i]) => [v, Math.sqrt(Math.abs(i))]);
  if (chosen.length < 3) return null;
  const vs = chosen.map(([v]) => v);
  const [a, b, r2] = lineFit(vs, chosen.map(([, s]) => s));
  return {
    v_from: vFrom, v_to: vTo,
    used_from: Math.min(...vs), used_to: Math.max(...vs), // 실제로 쓴 점의 전압 범위
    points: chosen.length,
    slope: a, intercept: b, r2,
    mu: (2 * l * a * a) / (C_OX * w), // cm²/V·s
    vth: -b / a, // V
  };
}

// ── 두 벌 비교 ───────────────────────────────────────────────

// 소자 하나: 자바스크립트로 2 V 구간을 다시 계산해 파이썬이 적어 둔 값(device.sweep)과 비교한다.
function matchesPython(device) {
  const close = (x, y) => Math.abs(x - y) <= 1e-9 * Math.max(Math.abs(x), Math.abs(y));
  const mine = windows(device.points).map(([a, b]) => saturationFit(device.points, device.w, device.l, a, b));
  return mine.length === device.sweep.length && mine.every((r, k) => {
    const p = device.sweep[k];
    return r && close(r.mu, p.mu) && close(r.vth, p.vth) && close(r.r2, p.r2) &&
      turnedOn(r) === p.on && vthBeforeWindow(r) === p.valid;
  });
}

function selfCheck(devices) {
  const ok = devices.filter(matchesPython).length;
  const line = document.getElementById("selfcheck");
  line.textContent = `파이썬 계산과 일치: 소자 ${devices.length}개 중 ${ok}개`;
  if (ok !== devices.length) line.style.color = "#B3361B";
}

// ── 화면 ─────────────────────────────────────────────────────

const $ = (id) => document.getElementById(id);
const num = (x, digits = 3) => String(Number(x.toPrecision(digits)));
const say = (text) => { $("msg").textContent = text; };
let current = null; // 지금 그래프에 올라와 있는 소자: {label, w, l, points}

// 소자를 그래프에 올린다. 처음 구간은 구동 방향 측정 범위의 가운데 3분의 1 (결과를 보고 고르는 것이 아니다).
function select(device) {
  current = device;
  $("title").textContent = device.label;
  $("w").value = device.w ?? "";
  $("l").value = device.l ?? "";
  const vs = device.points.map(([v]) => v);
  for (const id of ["from", "to", "fromRange", "toRange"]) {
    $(id).min = Math.min(...vs);
    $(id).max = Math.max(...vs);
  }
  const end = vs.reduce((far, v) => (Math.abs(v) > Math.abs(far) ? v : far));
  $("from").value = $("fromRange").value = Math.round((end / 3) * 10) / 10;
  $("to").value = $("toRange").value = Math.round(((2 * end) / 3) * 10) / 10;
  document.querySelectorAll("#icons button").forEach((b, k) => b.setAttribute("aria-pressed", DEVICES[k] === device));
  render();
}

function render() {
  const w = Number($("w").value), l = Number($("l").value), sized = w > 0 && l > 0;
  const r = saturationFit(current.points, w, l, Number($("from").value), Number($("to").value));
  const on = r && turnedOn(r);
  $("mu").textContent = !r ? "구간 안의 점이 3개보다 적습니다" : !on ? "계산 안 함 (기울기가 0 이하)"
    : !sized ? "W와 L을 적어 주세요" : `${num(r.mu, 4)} cm²/V·s`;
  $("vth").textContent = on ? `${r.vth.toFixed(2)} V` : "–";
  $("r2").textContent = r ? r.r2.toFixed(4) : "–";
  $("used").textContent = r ? `${r.used_from} ~ ${r.used_to} V, ${r.points}점` : "–";
  drawChart(r, on);
  drawBars(w, l, sized);
}

// √|I|–V 곡선, 고른 구간(연한 띠), 맞춘 직선(실선), 직선이 전압 축과 만나는 점 Vth 까지의 연장(점선).
function drawChart(r, on) {
  const pts = current.points.map(([v, i]) => [v, Math.sqrt(Math.abs(i))]);
  const vs = pts.map(([v]) => v), x0 = Math.min(...vs), x1 = Math.max(...vs), top = Math.max(...pts.map(([, s]) => s));
  const X = (v) => 56 + ((v - x0) / (x1 - x0)) * 408, Y = (s) => 256 - (s / top) * 236;
  let svg = `<line x1="56" y1="256" x2="464" y2="256" stroke="#1C2128"/><line x1="56" y1="20" x2="56" y2="256" stroke="#1C2128"/>`;
  for (let v = Math.ceil(x0 / 5) * 5; v <= x1; v += 5) {
    svg += `<line x1="${X(v)}" y1="256" x2="${X(v)}" y2="261" stroke="#1C2128"/><text x="${X(v)}" y="276" text-anchor="middle">${v}</text>`;
  }
  svg += `<text x="464" y="294" text-anchor="end">전압 (V)</text><text x="50" y="260" text-anchor="end">0</text>` +
    `<text x="50" y="24" text-anchor="end">${top.toExponential(1)}</text><text x="62" y="14">√|I| (√A)</text>`;
  if (r) {
    const a = Math.min(r.used_from, r.used_to), b = Math.max(r.used_from, r.used_to);
    svg += `<rect x="${X(a)}" y="20" width="${X(b) - X(a)}" height="236" fill="#14525A" opacity=".1"/>`;
  }
  svg += pts.map(([v, s]) => `<circle cx="${X(v).toFixed(1)}" cy="${Y(s).toFixed(1)}" r="1.6" fill="#6B726E"/>`).join("");
  if (r) {
    const line = (v) => r.slope * v + r.intercept;
    svg += `<line x1="${X(r.used_from)}" y1="${Y(line(r.used_from))}" x2="${X(r.used_to)}" y2="${Y(line(r.used_to))}" stroke="#14525A" stroke-width="2.5"/>`;
    if (on && r.vth >= x0 && r.vth <= x1) {
      const near = Math.abs(r.used_from - r.vth) < Math.abs(r.used_to - r.vth) ? r.used_from : r.used_to;
      svg += `<line x1="${X(r.vth)}" y1="256" x2="${X(near)}" y2="${Y(line(near))}" stroke="#14525A" stroke-dasharray="4 4"/>`;
    }
  }
  $("chart").innerHTML = svg; // 숫자로만 만든 글자다. 파일에서 온 글자는 넣지 않는다.
  $("chart").setAttribute("aria-label", `${current.label}의 √|I|–V 곡선. 측정점 ${pts.length}개, 전압 ${x0} ~ ${x1} V.`);
}

// 2 V 구간마다 계산한 이동도 막대. 가장 큰 값만 적색, 식과 어긋난 구간은 연하게.
function drawBars(w, l, sized) {
  const box = $("bars");
  box.textContent = "";
  if (!sized) return;
  const shown = windows(current.points).map(([a, b]) => saturationFit(current.points, w, l, a, b)).filter((r) => r && turnedOn(r));
  const top = Math.max(...shown.map((r) => r.mu));
  for (const r of shown) {
    const bar = document.createElement("div");
    bar.className = "bar " + (r.mu === top ? "max" : vthBeforeWindow(r) ? "" : "off");
    bar.innerHTML = `<span class=k>${r.used_from} ~ ${r.used_to} V</span><span class=t><i style="width:${(100 * r.mu) / top}%"></i></span><span class=v>${num(r.mu)}</span>`;
    box.append(bar);
  }
}

// 방문자가 놓은 파일. 브라우저 안에서만 읽는다.
function loadFile(file) {
  if (!file) return;
  if (file.size > 5e6) return say("읽을 수 없습니다: 파일이 5 MB보다 큽니다");
  file.text().then((text) => {
    const points = mobilityPoints(text, file.name);
    if (points.length < 3) throw new Error("측정점이 3개보다 적습니다");
    // 수업 파일의 이름 규칙: 끝 네 자리가 W 두 자리 + L 두 자리 (read_raw.py 의 device 와 같다)
    const m = /^[A-Za-z]+(\d\d)(\d\d)\.[^.]+$/.exec(file.name);
    select({ label: file.name, w: m ? Number(m[1]) : null, l: m ? Number(m[2]) : null, points });
    say(m ? `${file.name}: 파일 이름을 W ${Number(m[1])}, L ${Number(m[2])}로 읽었습니다. 다르면 고쳐 주세요.` : `${file.name}: W와 L을 적어 주세요.`);
  }).catch((e) => say(`읽을 수 없습니다: ${e.message}`));
}

function start() {
  DEVICES.forEach((device, k) => {
    const [material, size] = device.label.split(" · ");
    const b = document.createElement("button");
    b.type = "button";
    b.draggable = true;
    b.innerHTML = `<b>${material}</b>${size}`; // data.js 는 build.py 가 만든 글자다
    b.addEventListener("click", () => { select(device); say(""); });
    b.addEventListener("dragstart", (e) => e.dataTransfer.setData("text/plain", String(k)));
    $("icons").append(b);
  });
  for (const id of ["from", "to", "w", "l"]) $(id).addEventListener("input", () => { if ($(id + "Range")) $(id + "Range").value = $(id).value; render(); });
  for (const id of ["from", "to"]) $(id + "Range").addEventListener("input", () => { $(id).value = $(id + "Range").value; render(); });
  $("file").addEventListener("change", (e) => loadFile(e.target.files[0]));
  // 페이지 어디에 놓아도 브라우저가 그 파일을 열어 버리지 않게 한다.
  for (const type of ["dragover", "drop"]) document.addEventListener(type, (e) => e.preventDefault());
  for (const zone of [$("plot"), $("drop")]) {
    zone.addEventListener("dragover", () => zone.classList.add("over"));
    zone.addEventListener("dragleave", () => zone.classList.remove("over"));
    zone.addEventListener("drop", (e) => {
      zone.classList.remove("over");
      const device = DEVICES[e.dataTransfer.getData("text/plain")];
      if (e.dataTransfer.files.length) loadFile(e.dataTransfer.files[0]);
      else if (device) { select(device); say(""); }
    });
  }
  select(DEVICES.find((d) => d.label === "a-IGZO · W20/L4") ?? DEVICES[0]);
}

if (typeof document !== "undefined") { // DEVICES 는 data.js 에 있다
  selfCheck(DEVICES);
  start();
}
