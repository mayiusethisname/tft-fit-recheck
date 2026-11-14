// 자바스크립트 계산(site/app.js)을 원자료와 파이썬 값에 대조한다. 실행: node tests/check_js.js
// node 는 이 확인에만 쓴다. 사이트와 파이썬 계산에는 필요 없다.
const fs = require("fs");
const site = __dirname + "/../site/";
const code = fs.readFileSync(site + "data.js", "utf8") + fs.readFileSync(site + "app.js", "utf8") +
  "\nreturn {DEVICES, mobilityPoints, saturationFit, matchesPython, windows};";
const m = new Function(code)();
const raw = "D:/AMD/8주차/TFT DATA/";
const names = ["aSi2002.DAT","aSi2006.DAT","aSi2020.DAT","IGZO2002.csv","IGZO2004.csv","IGZO2010.csv","LTPS1002.DAT","LTPS1005.DAT","LTPS1010.DAT"];
names.forEach((name, k) => {
  const pts = m.mobilityPoints(fs.readFileSync(raw + name, "latin1"), name);
  const d = m.DEVICES[k];
  const same = JSON.stringify(pts) === JSON.stringify(d.points);
  console.log(d.label.padEnd(18), "JS가 원자료에서 읽은 점", pts.length, "| 파이썬이 읽은 것과 같음:", same, "| 구간 계산 일치:", m.matchesPython(d));
});
const d = m.DEVICES[4], r = m.saturationFit(d.points, d.w, d.l, 5.5, 9.5);
console.log(d.label, "5.5~9.5 V  a =", r.slope.toExponential(6), " b =", r.intercept.toExponential(6), " R² =", r.r2.toFixed(4), " μ =", r.mu.toPrecision(4), " Vth =", r.vth.toPrecision(4), " 점", r.points);
// 비교가 틀린 것을 정말 잡아내는지: 전류 하나를 1% 바꿔 본다
const broken = JSON.parse(JSON.stringify(d)); broken.points[150][1] *= 1.01;
console.log("전류 하나를 1% 바꾼 뒤 일치:", m.matchesPython(broken));
try { m.mobilityPoints("아무 글자\n1,2,3", "x.csv"); } catch (e) { console.log("형식이 다른 파일:", e.message); }
