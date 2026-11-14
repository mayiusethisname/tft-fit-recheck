"""계산 결과를 results/*.json 과 site/index.html 로 쓴다.

    python -m recheck build

화면의 모든 숫자는 cases.py의 caseN_data()에서 온다. site/ 와 results/ 는 손으로 고치지 않는다.
원자료는 내보내지 않는다 (docs/adr/0001). 예외로 9개 소자의 이동도 측정만 site/data.js 로 내보낸다 (docs/adr/0004).
"""
import json
from pathlib import Path

from recheck import cases, read_raw

ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/mayiusethisname/tft-fit-recheck"

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#FFFFFF;color:#1C2128;font-family:Pretendard,system-ui,sans-serif;font-size:1rem;line-height:1.75;word-break:keep-all;overflow-wrap:break-word}
a{color:#14525A}a:hover{color:#0B3A40}
.wrap{max-width:1040px;margin:0 auto;padding:0 5%;box-sizing:content-box}
nav{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 24px;padding:8px 0;border-bottom:1px solid #CDD1CC}
nav b{font-weight:700}
nav div{display:flex;flex-wrap:wrap;gap:0 24px;font-size:.875rem}
nav a{padding:10px 0;line-height:24px;text-decoration:none}
header{padding:40px 0 32px}
h1{margin:0 0 24px;font-size:clamp(2rem,5vw,3rem);line-height:1.35;font-weight:700;letter-spacing:-.02em;max-width:880px}
h2{margin:0 0 8px;font-size:1.75rem;line-height:1.4;font-weight:700;letter-spacing:-.01em}
h3{margin:0 0 8px;font-size:1rem;font-weight:700}
p{margin:0 0 16px;max-width:720px}
.sub,.note{color:#4A5058}
.note,.small{font-size:.875rem;line-height:1.7}
section{border-top:1px solid #1C2128;padding:32px 0 64px}
figure{margin:0 0 24px;min-width:0}
figcaption{font-weight:600;line-height:1.5;margin-bottom:16px}
figcaption span{font-weight:400;color:#4A5058}
.bar{display:flex;gap:16px;align-items:center;height:32px;font-family:'IBM Plex Mono',monospace;font-size:.875rem}
.bar .k{width:104px;flex:none;white-space:nowrap}
.bar .t{flex:1;min-width:0;border-left:1px solid #1C2128;height:100%;display:flex;align-items:center}
.bar .t i{display:block;height:16px;background:#6B726E}
.bar .v{width:72px;flex:none;text-align:right;font-weight:500;white-space:nowrap}
.bar.max .t i{background:#B3361B}.bar.max .v{color:#B3361B;font-weight:600}
.bar.off .t i{background:#CDD1CC}.bar.off{color:#4A5058}
ul{margin:0 0 16px;padding-left:20px;max-width:720px}
li{margin-bottom:8px}
footer{border-top:1px solid #1C2128;padding:24px 0 48px;font-size:.875rem;color:#4A5058}
.found{display:grid;grid-template-columns:320px 1fr;gap:8px 40px;padding:24px 0;border-top:1px solid #CDD1CC}
.found:first-of-type{border-top:0}
.found .fig{font-family:'IBM Plex Mono',monospace;font-size:1.75rem;font-weight:600;line-height:1.4;white-space:nowrap}
.found h3{font-size:1.125rem}
.found h3 small{font-size:.875rem;font-weight:400;color:#4A5058;margin-left:8px}
.found p{margin:0}
.steps{margin:16px 0;padding-left:24px;max-width:720px}
.steps li{margin-bottom:16px;padding-left:4px}
.eq{display:block;margin-top:4px;font-family:'IBM Plex Mono',monospace;color:#14525A}
@media(max-width:640px){.found{grid-template-columns:1fr}}
.tool{display:flex;flex-wrap:wrap;gap:32px 48px}
.files{flex:1 1 220px;min-width:0}
.plot{flex:999 1 440px;min-width:0;outline:2px dashed transparent;outline-offset:12px}
.plot.over{outline-color:#14525A}
#icons{display:grid;grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:8px;margin-bottom:16px}
#icons button{font:inherit;font-size:.875rem;line-height:1.4;text-align:left;padding:10px 12px;min-height:60px;background:#fff;color:inherit;border:1px solid #CDD1CC;border-radius:4px;cursor:grab}
#icons button b{display:block}
#icons button:hover{border-color:#1C2128}
#icons button[aria-pressed=true]{border-color:#1C2128;box-shadow:inset 0 0 0 1px #1C2128}
.drop{display:block;border:1px dashed #6B726E;border-radius:4px;padding:16px 12px;margin-bottom:12px;text-align:center;font-weight:600;cursor:pointer}
.drop small{display:block;font-weight:400;color:#4A5058}
.drop input{position:absolute;opacity:0;width:1px;height:1px}
.drop:hover,.drop:focus-within{border-color:#14525A;color:#14525A}
#msg:empty{display:none}#msg{color:#1C2128;font-weight:600}
#chart{display:block;width:100%;max-width:600px;height:auto;margin:8px 0 16px}
#chart text{font-size:14px;fill:#4A5058}
.controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:8px 32px;margin-bottom:16px;font-size:.875rem}
.controls label{display:flex;align-items:center;gap:8px;white-space:nowrap}
.controls input[type=range]{flex:1;min-width:0;accent-color:#14525A}
.controls input[type=number]{font:inherit;font-family:'IBM Plex Mono',monospace;width:72px;padding:6px 8px;border:1px solid #6B726E;border-radius:4px;margin-left:auto}
.controls input[type=range]+input{margin-left:0}
#result{display:flex;flex-wrap:wrap;gap:8px 40px;margin:0 0 16px;padding:16px 0;border-top:1px solid #1C2128;border-bottom:1px solid #CDD1CC}
#result dt{font-size:.875rem;color:#4A5058}
#result dd{margin:0;font-family:'IBM Plex Mono',monospace;font-weight:500}
#result dd.main{font-size:1.75rem;font-weight:600;line-height:1.3}
"""


def num(x, digits=3):
    """화면에 쓰는 숫자 표기. 유효숫자 3자리."""
    return f"{x:.{digits}g}"


def span(r):
    return f"{r['used_from']:g} ~ {r['used_to']:g} V"


def page(c):
    c2, c3 = c["2"], c["3"]
    far = c2["far"]
    lo, hi = min(far, key=lambda r: r["mu"]), max(far, key=lambda r: r["mu"])
    r2_min = min(r["r2"] for r in far)
    asi = [r for r in c3["sweeps"]["aSi2004.DAT"] if r["valid"]]
    ltps = [r for r in c3["sweeps"]["LTPS1005.DAT"] if r["valid"]]
    ltps_top = max(ltps, key=lambda r: r["mu"])

    # 재료마다 구간에 따라 이동도가 어떻게 달라지는가: (재료, 숫자, 한 줄). 숫자는 cases.py 에서 온다.
    materials = [
        ("a-IGZO", "대형 OLED TV에 쓰이는 산화물 반도체", f"{num(lo['mu'])} → {num(hi['mu'])}",
         "전압이 올라갈수록 계속 커집니다."),
        ("a-Si", "LCD에 오래 쓰여 온 비정질 실리콘", f"{num(asi[0]['mu'])} → {num(asi[-1]['mu'])}",
         "완만하게 커집니다."),
        # 정점 뒤의 값은 적지 않는다. 마지막 구간(−20 ~ −18 V)은 측정이 끊긴 자리라 숫자로 쓸 수 없다.
        ("LTPS", "스마트폰 OLED에 쓰이는 저온 폴리실리콘", f"{num(ltps[0]['mu'])} → {num(ltps_top['mu'])}",
         f"{span(ltps_top)}에서 가장 크고, 그 뒤로는 작아집니다."),
    ]
    materials_html = "".join(f"<div class=found><div class=fig>{fig}</div><div><h3>{name} <small>{use}</small></h3>"
                             f"<p>{text}</p></div></div>" for name, use, fig, text in materials)

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TFT 피팅 구간 비교 도구</title>
<meta name="description" content="TFT 측정 파일을 놓으면 그래프와 이동도를 계산하는 도구.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>{CSS}</style>
</head>
<body><div class=wrap>
<nav><b>TFT 피팅 구간 비교 도구</b><div><a href="#materials">재료별 차이</a><a href="#how">계산 방법</a><a href="#why">만든 이유</a><a href="{REPO_URL}">GitHub</a></div></nav>
<header>
<h1>TFT 측정 파일을 놓으면 이동도를 계산합니다.</h1>
<p class=sub>TFT는 화면의 화소를 켜고 끄는 스위치입니다. 이동도는 그 안에서 전하가 얼마나 잘 움직이는지를 나타내는 값으로, 그래프에 그은 직선의 기울기로 구합니다. 직선을 어느 구간에 긋느냐에 따라 이 값이 {c2['far_spread']:.0f}배까지 달라집니다. 구간을 직접 옮겨 보세요.</p>
</header>
<section id=tool class=tool>
<div class=files>
<h3>측정 파일</h3>
<p class=note>그래프로 끌어다 놓거나 누르세요.</p>
<div id=icons></div>
<label id=drop class=drop>내 파일 놓기 또는 고르기<small>DAT · CSV</small><input type=file id=file accept=".dat,.csv"></label>
<p class=note>파일은 이 브라우저 안에서만 읽습니다.</p>
<p id=msg class=note role=status></p>
</div>
<div id=plot class=plot>
<h2 id=title></h2>
<svg id=chart viewBox="0 0 480 300" role=img></svg>
<div class=controls>
<label>구간 시작 <input type=range id=fromRange step=0.1 aria-label="구간 시작 조절"><input type=number id=from step=0.1 aria-label="구간 시작 (V)"> V</label>
<label>구간 끝 <input type=range id=toRange step=0.1 aria-label="구간 끝 조절"><input type=number id=to step=0.1 aria-label="구간 끝 (V)"> V</label>
<label>채널 폭 W <input type=number id=w min=0 step=any> µm</label>
<label>채널 길이 L <input type=number id=l min=0 step=any> µm</label>
</div>
<dl id=result aria-live=polite>
<div><dt>이동도 μ</dt><dd id=mu class=main></dd></div>
<div><dt>문턱전압 Vth</dt><dd id=vth></dd></div>
<div><dt>R²</dt><dd id=r2></dd></div>
<div><dt>쓴 점</dt><dd id=used></dd></div>
</dl>
<p class=note>문턱전압은 소자가 켜지기 시작하는 전압입니다. R²는 직선이 점에 맞는 정도로, 1이면 완전히 맞습니다.</p>
<figure><figcaption>2 V 구간마다 계산한 이동도 <span>단위 cm²/V·s</span></figcaption><div id=bars></div>
<p class=note style="margin-top:12px">연한 막대는 소자가 다 켜지기 전의 구간입니다(문턱전압이 구간 안이나 뒤에 나옴). a-IGZO W20/L4는 나머지 {len(far)}개 구간 모두 직선이 잘 맞는데도(R² {r2_min:.4f} 이상) 이동도가 {num(lo['mu'])} ~ {num(hi['mu'])}, {c2['far_spread']:.1f}배 차이 납니다.</p></figure>
</div>
</section>
<section id=materials>
<h2>재료마다 다릅니다</h2>
<p class=sub>계산식은 이동도가 전압과 무관하게 일정하다고 가정합니다. 실제 소자는 그렇지 않아서 구간마다 값이 달라집니다. 2 V 구간을 낮은 전압에서 높은 전압으로 옮기며 구한 이동도입니다(cm²/V·s).</p>
{materials_html}
</section>
<section id=how>
<h2>계산 방법</h2>
<ol class=steps>
<li><b>전류의 제곱근을 전압에 대해 그립니다.</b> 소자가 켜진 뒤에는 직선에 가까워집니다.<span class=eq>√|I| = a·V + b</span></li>
<li><b>고른 구간에 직선을 맞춥니다.</b> 기울기 a가 이동도를 정합니다.<span class=eq>μ = 2·L·a² / (C·W)</span></li>
<li><b>직선이 전압 축과 만나는 점이 문턱전압입니다.</b><span class=eq>Vth = −b / a</span></li>
</ol>
<p class=note>게이트와 드레인 전압을 함께 올린 측정(포화 영역)에 쓰는 식입니다. W, L은 채널 폭과 길이, C는 절연막 용량(1.75×10⁻⁸ F/cm²)입니다.</p>
</section>
<section id=why>
<h2>만든 이유</h2>
<p>수업의 측정 파일은 DAT와 CSV가 섞여 있어, 형식마다 그래프 매크로를 따로 짜야 했습니다. 직선 구간은 눈대중으로 골랐습니다. 파일을 놓기만 하면 그래프가 나오고, 구간에 따른 차이를 한눈에 볼 수 있게 만들었습니다.</p>
</section>
<section id=next>
<h2>다음에 더할 것</h2>
<ul>
<li><b>구간 제안.</b> 이동도가 가장 덜 변하는 구간을 찾아 먼저 보여 주기.</li>
<li><b>다른 장비의 파일.</b> 열 이름이 다른 측정 파일도 읽기.</li>
</ul>
</section>
<section id=learned>
<h2>배운 것</h2>
<ul>
<li><b>잘 맞는 것과 맞는 값은 다릅니다.</b> 직선이 깔끔하게 맞아도, 구간을 옮기면 값이 달라졌습니다. 결과 하나를 믿기 전에 조건을 바꿔 다시 계산합니다.</li>
<li><b>계산보다 입력이 먼저입니다.</b> 원본 숫자가 그대로 들어왔는지부터 확인합니다.</li>
<li><b>반복되는 손작업은 도구로 바꿉니다.</b> 형식 차이를 없애자, 비교에 쓸 시간이 생겼습니다.</li>
</ul>
</section>
<footer><a href="{REPO_URL}">GitHub</a></footer>
</div><script src="data.js"></script><script src="app.js"></script></body></html>
"""


def build():
    c = {str(n): getattr(cases, f"case{n}_data")() for n in range(1, 6)}
    sweep = {p.name: cases.sweep_file(p.name) for p in read_raw.raw_files()}
    public = json.loads(json.dumps(c))
    for f in public["5"]["files"]:  # 원자료의 전류값은 내보내지 않고 비율만 남긴다
        del f["hightrans"], f["mobility"]
    for folder in ("results", "site"):
        (ROOT / folder).mkdir(exist_ok=True)
    dump = lambda data: json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    (ROOT / "results" / "cases.json").write_text(dump(public), encoding="utf-8", newline="\n")
    (ROOT / "results" / "sweep.json").write_text(dump(sweep), encoding="utf-8", newline="\n")
    (ROOT / "site" / "index.html").write_text(page(c), encoding="utf-8", newline="\n")
    # 도구 화면용 자료 (adr/0004): 이미 공개돼 있던 9개 소자의 이동도 측정만. 원래 파일 이름은 넣지 않는다.
    names = {"IGZO": "a-IGZO", "aSi": "a-Si", "LTPS": "LTPS"}
    devices = []
    for name in cases.PUBLISHED_BY_OLD_TOOL:
        path = read_raw.RAW_DIR / name
        material, w, l = read_raw.device(path)
        devices.append({"label": f"{names[material]} · W{w:g}/L{l:g}", "w": w, "l": l,
                        "points": read_raw.mobility_points(path), "sweep": sweep[name]})
    lines = ",\n".join(json.dumps(d, ensure_ascii=False, separators=(",", ":")) for d in devices)
    # 스크립트 파일로 쓴다. JSON 파일을 따로 불러오는 방식은 index.html을 더블클릭으로 열면 막힌다.
    (ROOT / "site" / "data.js").write_text(f"const DEVICES = [\n{lines}\n];\n", encoding="utf-8", newline="\n")
    print("썼습니다: results/cases.json, results/sweep.json, site/index.html, site/data.js")
