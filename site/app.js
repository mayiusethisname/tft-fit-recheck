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

if (typeof document !== "undefined") selfCheck(DEVICES); // DEVICES 는 data.js 에 있다
