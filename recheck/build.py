"""계산 결과를 results/*.json 과 site/index.html 로 쓴다.

    python -m recheck build

화면의 모든 숫자는 cases.py의 caseN_data()에서 온다. site/ 와 results/ 는 손으로 고치지 않는다.
원자료의 측정값 자체는 내보내지 않는다 (docs/adr/0001). 구간별로 계산한 값과 개수, 비율만 내보낸다.
"""
import json
from math import ceil, floor, log10
from pathlib import Path

from recheck import cases, read_raw

ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/mayiusethisname/tft-fit-recheck"

# 작성자가 명령을 직접 돌려 화면의 숫자와 대조한 날짜. 항목 번호 → "YYYY-MM-DD". 확인한 뒤에만 적는다.
CONFIRMED = {}

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
.axis{display:flex;gap:16px;border-top:1px solid #1C2128;font-family:'IBM Plex Mono',monospace;font-size:.875rem;color:#4A5058}
.axis .k{width:104px;flex:none}.axis .v{width:72px;flex:none}
.axis .t{flex:1;display:flex;justify-content:space-between;padding-top:4px}
.scroll{overflow-x:auto;margin-bottom:16px}
table{width:100%;border-collapse:collapse;line-height:1.6}
th{text-align:left;font-size:.875rem;font-weight:500;color:#4A5058;padding:8px 24px 8px 0;border-bottom:1px solid #1C2128;white-space:nowrap}
td{padding:12px 24px 12px 0;border-bottom:1px solid #CDD1CC;vertical-align:top}
tr:last-child td{border-bottom-color:#1C2128}
td:first-child{white-space:nowrap}
td.n,th.n{font-family:'IBM Plex Mono',monospace;font-size:.875rem;text-align:right;white-space:nowrap}
th.n{font-family:inherit}
td.warn{color:#B3361B;font-weight:600}
.state{white-space:nowrap;font-size:.875rem;font-weight:500}
.state i{display:inline-block;width:14px;height:14px;border:2px solid #1C2128;margin-right:8px;vertical-align:-2px}
.state.done i{background:#14525A;border-color:#14525A}
.state small{display:block;font-family:'IBM Plex Mono',monospace;font-weight:400;margin-left:22px}
.item{border-top:1px solid #CDD1CC;padding:24px 0 8px}
.item:first-of-type{border-top:0;padding-top:8px}
code{font-family:'IBM Plex Mono',monospace;font-size:.875rem;background:#E7E9E5;padding:2px 6px}
ul{margin:0 0 16px;padding-left:20px;max-width:720px}
li{margin-bottom:8px}
@media(max-width:640px){.check thead{display:none}.check tr{display:block;padding:12px 0;border-bottom:1px solid #CDD1CC}.check tr:last-child{border-bottom-color:#1C2128}.check td{display:block;border:0;padding:2px 0}}
footer{border-top:1px solid #1C2128;padding:24px 0 48px;font-size:.875rem;color:#4A5058}
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


def table(head, rows):
    """head: (제목, 숫자 열인가) 목록.  rows: 칸 문자열 목록의 목록. 칸이 '!'로 시작하면 주의색."""
    out = ["<div class=scroll><table><thead><tr>"]
    out += [f"<th scope=col{' class=n' if n else ''}>{h}</th>" for h, n in head]
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        for (_, n), cell in zip(head, row):
            warn = cell.startswith("!")
            cls = " ".join(c for c in ("n" if n else "", "warn" if warn else "") if c)
            out.append(f"<td{f' class=\"{cls}\"' if cls else ''}>{cell.lstrip('!')}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def bars(results, caption, device):
    """구간별 이동도 가로 막대 그림. 가장 큰 값만 적색, 식과 어긋난 구간은 연하게."""
    shown = [r for r in results if r["on"]]
    top = max(r["mu"] for r in shown)
    step = next(s * 10 ** floor(log10(top)) for s in (1, 2, 5, 10) if top / (s * 10 ** floor(log10(top))) <= 4)
    ticks = [step * k for k in range(ceil(top / step - 1e-9) + 1)]
    label = ", ".join(f"{span(r)} {num(r['mu'])}" for r in shown)
    out = [f"<figure><figcaption>{caption} <span>{device}</span></figcaption>",
           f'<div role=img aria-label="구간별 포화 이동도 막대 그림, 단위 cm²/V·s. {label}">']
    for r in shown:
        cls = "max" if r["mu"] == top else "" if r["valid"] else "off"
        out.append(f'<div class="bar {cls}"><span class=k>{span(r)}</span>'
                   f'<span class=t><i style="width:{100 * r["mu"] / ticks[-1]:.2f}%"></i></span>'
                   f'<span class=v>{num(r["mu"])}</span></div>')
    out.append("<div class=axis><span class=k></span><span class=t>"
               + "".join(f"<span>{t:g}</span>" for t in ticks) + "</span><span class=v></span></div></div>")
    out.append("<p class=note style='margin-top:12px'>단위 cm²/V·s. 연한 막대는 그 구간에서 나온 문턱전압이 구간 시작점보다 "
               "앞에 있지 않은 구간입니다.</p></figure>")
    return "".join(out)


def state(n):
    if n in CONFIRMED:
        return f'<span class="state done"><i></i>직접 확인함<small>{CONFIRMED[n]}</small></span>'
    return '<span class=state><i></i>직접 확인 전</span>'


def page(c):
    c1, c2, c3, c4, c5 = (c[k] for k in "12345")
    far, near = c2["far"], c2["near"]
    lo, hi = min(far, key=lambda r: r["mu"]), max(far, key=lambda r: r["mu"])
    odd = max(c5["files"], key=lambda f: f["ratio"])
    rest = [f["ratio"] for f in c5["files"] if f is not odd]
    uv = c4["files"][0]
    asi, ltps = c3["sweeps"]["aSi2004.DAT"], c3["sweeps"]["LTPS1005.DAT"]
    asi_ok = [r for r in asi if r["valid"]]
    ltps_top = max(ltps, key=lambda r: r["mu"])
    r2_min = min(r["r2"] for r in far)

    checklist = [
        ("숫자가 원본 그대로인가", f"음수 전류 {c1['total']}개가 양수로 바뀌어 있었습니다"),
        ("“여러 후보”가 정말 서로 다른가", "후보 3개가 0.5 V씩만 다른 옆 구간이었습니다"),
        ("계산식의 전제가 맞는가", "식은 이동도가 일정하다고 보는데, 실제로는 전압에 따라 달라졌습니다"),
        ("이 자료로 구할 수 있는 값인가", "측정 범위 밖에 있는 값을 계산해 냈습니다"),
        ("같은 파일의 다른 측정과 맞는가", f"한 측정만 전류가 {num(odd['ratio'])}배 작았습니다"),
    ]
    fit_head = [("피팅 구간", 0), ("이동도 (cm²/V·s)", 1), ("문턱전압 (V)", 1), ("R²", 1)]
    fit_rows = lambda rs: [[span(r), num(r["mu"], 4), f"{r['vth']:.3f}", f"{r['r2']:.4f}"] for r in rs]

    items = [
        (f"<p>AI가 처음 짠 코드는 전류를 절댓값으로 바꿔 옮겼습니다. 검사도 같은 변환을 거친 값끼리 비교해 통과했습니다. "
         f"원본 9개 파일의 음수 전류는 {c1['total']}개입니다.</p>"
         + table([("파일", 0), ("측정점", 1), ("음수 전류", 1)],
                 [[f["name"], str(f["points"]), str(f["negative"])] for f in c1["files"]])
         + "<p class=note>바뀌었다는 사실은 당시 변경 기록이, 개수는 이번 재계산이 근거입니다.</p>"),
        (f"<p>AI는 a-IGZO W20/L4에 구간 후보 3개를 냈습니다. 0.5 V씩 밀린 옆 구간이라 이동도가 "
         f"{num(near[0]['mu'])} ~ {num(near[-1]['mu'])}로 비슷했고, 값이 안정적으로 보였습니다. "
         f"겹치지 않는 2 V 구간으로 나누면 {num(lo['mu'])} ~ {num(hi['mu'])}입니다.</p>"
         + "<h3>AI의 후보 3개</h3>" + table(fit_head, fit_rows(near))
         + "<h3>겹치지 않는 2 V 구간</h3>" + table(fit_head, fit_rows(far))
         + f"<p class=note>R²는 모두 {r2_min:.4f} 이상입니다. 직선이 잘 맞는다는 것만으로는 구간을 가릴 수 없습니다.</p>"),
        (f"<p>식은 이동도가 전압과 무관하게 일정하다고 가정합니다. 실제로는 a-IGZO는 계속 커지고, "
         f"a-Si는 조금씩 커지고({num(asi_ok[0]['mu'])} → {num(asi_ok[-1]['mu'])}), "
         f"LTPS는 {span(ltps_top)}에서 {num(ltps_top['mu'])}까지 커졌다가 작아집니다.</p>"
         + bars(asi, "그림 2. 구간별 포화 이동도", "a-Si W20/L4")
         + bars(ltps, "그림 3. 구간별 포화 이동도", "LTPS W10/L5")
         + "<h3>수업 예시 구간 15 ~ 20 V</h3>"
         + table([("파일", 0), ("실제로 쓴 점", 0), ("이동도 (cm²/V·s)", 1), ("R²", 1)],
                 [[r["name"], span(r), num(r["mu"]), f"{r['r2']:.4f}"] for r in c3["example"]])
         + "<p class=note>a-IGZO는 18 V까지만 측정됐습니다. LTPS는 −15 ~ −20 V입니다.</p>"),
        (f"<p>밴드갭은 빛을 흡수하기 시작하는 에너지에서 구합니다. 측정 범위는 {uv['nm_min']:g} ~ {uv['nm_max']:g} nm"
         f"({uv['ev_min']:.3f} ~ {uv['ev_max']:.3f} eV)입니다. 결정질 실리콘의 밴드갭 약 {c4['si_gap_ev']} eV는 범위 밖입니다. "
         f"그런데 AI는 Poly-Si의 밴드갭을 계산해 “안정”이라고 표시했습니다.</p>"
         + table([("파일", 0), ("측정점", 1), ("파장 (nm)", 1), ("광자 에너지 (eV)", 1)],
                 [[f["name"], str(f["points"]), f"{f['nm_min']:g} ~ {f['nm_max']:g}",
                   f"{f['ev_min']:.3f} ~ {f['ev_max']:.3f}"] for f in c4["files"]])),
        (f"<p>한 파일에는 같은 소자를 여러 조건으로 잰 측정이 들어 있습니다. 게이트 18 V의 전류를 두 측정에서 꺼내 나누면 "
         f"1 이하여야 합니다. {odd['name']}만 {num(odd['ratio'])}이고, 나머지 넷은 {num(min(rest))} ~ {num(max(rest))}입니다.</p>"
         + table([("파일", 0), ("드레인 10 V 전류 ÷ 드레인 18 V 전류", 1)],
                 [[f["name"], ("!" if f is odd else "") + num(f["ratio"])] for f in c5["files"]])
         + "<p class=note>원인은 모릅니다. 이 파일의 이동도는 쓰지 않습니다.</p>"),
    ]

    body = [f"""<!doctype html>
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
<nav><b>TFT 피팅 구간 비교 도구</b><div><a href="#checklist">검수 기준표</a><a href="#recalc">다시 계산</a><a href="#log">AI 협업 기록</a><a href="#limits">한계</a><a href="{REPO_URL}">GitHub</a></div></nav>
<header>
<h1>TFT 측정 파일을 놓으면 이동도를 계산합니다.</h1>
<p class=sub>이동도는 그래프에 그은 직선의 기울기로 구합니다. 그런데 직선을 어느 구간에 긋느냐에 따라 기울기가 달라집니다. 같은 측정에서 구간만 바꿔도 이동도가 {c2['far_spread']:.0f}배까지 달라집니다. 구간을 직접 옮겨 보세요.</p>
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
<label>구간 시작 <input type=range id=fromRange step=0.1 aria-label="구간 시작 조절"><input type=number id=from step=0.1> V</label>
<label>구간 끝 <input type=range id=toRange step=0.1 aria-label="구간 끝 조절"><input type=number id=to step=0.1> V</label>
<label>채널 폭 W <input type=number id=w min=0 step=any> µm</label>
<label>채널 길이 L <input type=number id=l min=0 step=any> µm</label>
</div>
<dl id=result aria-live=polite>
<div><dt>이동도 μ</dt><dd id=mu class=main></dd></div>
<div><dt>문턱전압 Vth</dt><dd id=vth></dd></div>
<div><dt>R²</dt><dd id=r2></dd></div>
<div><dt>쓴 점</dt><dd id=used></dd></div>
</dl>
<p class=note>시작 구간은 측정 범위의 가운데 3분의 1입니다.</p>
<figure><figcaption>그림 1. 2 V 구간마다 계산한 이동도 <span>단위 cm²/V·s</span></figcaption><div id=bars></div>
<p class=note style="margin-top:12px">연한 막대는 식의 조건에 맞지 않는 구간입니다. a-IGZO W20/L4는 모든 구간에서 직선이 잘 맞는데도(R² {r2_min:.4f} 이상) 이동도가 {num(lo['mu'])} ~ {num(hi['mu'])}, {c2['far_spread']:.1f}배 차이 납니다.</p></figure>
</div>
</section>
<section id=why>
<h2>만든 이유</h2>
<p>수업의 측정 파일은 DAT와 CSV가 섞여 있어, 형식마다 그래프 매크로를 따로 짜야 했습니다. 직선 구간은 사람이 눈으로 골랐습니다. 이 두 가지를 AI와 함께 자동화했습니다.</p>
<p>만들면서 AI의 결과를 원본 파일로 다시 계산했고, 직접 확인해야 할 것을 다섯 가지로 정리했습니다.</p>
</section>
<section id=checklist>
<h2>검수 기준표</h2>
<p class=sub>AI의 결과에서 사람이 직접 확인할 다섯 가지입니다.</p>
<div class=scroll><table class=check><thead><tr><th scope=col>번호</th><th scope=col style="width:30%">직접 확인할 것</th><th scope=col>이 프로젝트에서 있었던 일</th><th scope=col style="width:144px">확인 상태</th></tr></thead><tbody>"""]
    for n, (what, happened) in enumerate(checklist, 1):
        body.append(f"<tr><td class=n style='text-align:left'>{n}</td><td><b>{what}</b></td>"
                    f"<td><a href='#case{n}' style='color:inherit;text-decoration:none'>{happened}</a></td><td>{state(n)}</td></tr>")
    body.append("""</tbody></table></div>
<p class=note>“직접 확인 전”은 AI가 계산했고, 작성자가 같은 명령으로 아직 대조하지 않은 항목입니다.</p>
</section>
<section id=recalc>
<h2>다시 계산</h2>
<p class=sub>항목마다 명령 한 줄로 원본에서 다시 계산합니다.</p>""")
    for n, ((what, _), html) in enumerate(zip(checklist, items), 1):
        body.append(f"<div class=item id=case{n}><h3>{n}. {what}</h3>{html}"
                    f"<p class=small>다시 계산하는 명령 <code>python -m recheck case {n}</code> &nbsp; {state(n)}</p></div>")
    body.append(f"""</section>
<section id=log>
<h2>AI 협업 기록</h2>
<p class=sub>코드는 AI(Claude)가 썼습니다. 방향과 채택 여부는 작성자가 정했습니다. 전체 기록은 <a href="{REPO_URL}/blob/main/docs/AI협업기록.md">docs/AI협업기록.md</a>에 있습니다.</p>
<h3>AI가 틀렸던 것</h3>
<ul>
<li>측정 범위를 넘는 구간을 말없이 잘라 계산했습니다. 15 ~ 20 V와 15 ~ 18 V의 결과가 같아서 드러났습니다.</li>
<li>미리 정한 “몇 배” 규칙이 LTPS에서 수백만 배를 냈습니다. 결과를 보고 규칙을 고치는 대신 그림 3으로 보여 줍니다.</li>
<li>첫 화면을 도구가 아닌 기록 문서로 만들었습니다. 작성자가 바로잡았습니다.</li>
<li>수업 자료를 읽지 않고 질문부터 했습니다. 읽고 나서야 구간을 고르는 기준이 자료에 없다는 것을 확인했습니다.</li>
</ul>
<h3>작성자가 바꾼 AI의 제안</h3>
<ul>
<li>검수 기준표가 중심인 고정 페이지를 파일을 놓는 도구로 바꿨습니다.</li>
<li>원자료 전체 대신 9개 소자의 이동도 측정만 올렸습니다.</li>
<li>절연막 용량 값의 출처는 따지지 않기로 했습니다. 수업에서 준 값입니다.</li>
</ul>
</section>
<section id=limits>
<h2>한계</h2>
<ul>
<li>도구는 구간을 골라 주지 않습니다. 이동도가 전압에 따라 변하는 소자에서는 어느 구간도 정답이 아닙니다.</li>
<li>측정 파일은 수업에서 여러 해 써 온 자료입니다. 작성자가 직접 측정하지 않았습니다.</li>
<li>절연막 용량은 수업에서 준 1.75×10⁻⁸ F/cm²을 세 재료에 똑같이 썼습니다.</li>
<li>채널 폭과 길이는 파일 이름에서 읽었습니다(IGZO2004 → W 20, L 4 µm).</li>
<li>드레인과 게이트를 함께 올린 측정이라고 가정했습니다.</li>
</ul>
</section>
<footer><code>python -m recheck build</code>로 다시 만듭니다. 계산 결과는 <a href="{REPO_URL}/tree/main/results">results/</a>에 있습니다. <span id="selfcheck"></span></footer>
</div><script src="data.js"></script><script src="app.js"></script></body></html>
""")
    return "".join(body)


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
