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
header{padding:64px 0 48px}
h1{margin:0 0 24px;font-size:clamp(2rem,5vw,3rem);line-height:1.35;font-weight:700;letter-spacing:-.02em;max-width:880px}
h2{margin:0 0 8px;font-size:1.75rem;line-height:1.4;font-weight:700;letter-spacing:-.01em}
h3{margin:0 0 8px;font-size:1rem;font-weight:700}
p{margin:0 0 16px;max-width:720px}
.sub,.note{color:#4A5058}
.note,.small{font-size:.875rem;line-height:1.7}
section{border-top:1px solid #1C2128;padding:32px 0 64px}
.hero{display:flex;flex-wrap:wrap;gap:32px 56px}
.hero>div{flex:1 1 260px;min-width:0}
.hero figure{flex:999 1 440px}
.big{font-family:'IBM Plex Mono',monospace;font-weight:600;font-size:clamp(4.5rem,11vw,7rem);line-height:1;color:#B3361B;letter-spacing:-.04em;margin:16px 0}
.big span{font-family:Pretendard,sans-serif;font-weight:700;font-size:.4em;letter-spacing:0;margin-left:4px}
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
        ("숫자가 원자료 그대로 옮겨졌는가",
         f"전류 {c1['total']}개가 절댓값으로 바뀌었고, 검사도 같은 변환을 써서 놓쳤습니다"),
        ("AI가 낸 “여러 후보”가 정말 서로 다른가",
         f"후보 3개가 0.5 V씩 밀린 옆 구간이라 값이 {num(c2['near_spread'])}배밖에 다르지 않았습니다"),
        ("계산식이 성립하는 조건인가",
         "식은 이동도가 일정하다고 가정하는데, 세 재료 모두 전압에 따라 달라졌습니다"),
        ("이 자료로 구할 수 있는 값인가",
         "Poly-Si의 흡수단이 측정 범위 밖인데 밴드갭이 “안정”으로 표시됐습니다"),
        ("같은 파일 안의 다른 측정과 맞는가",
         f"한 소자의 한 측정만 전류가 {num(odd['ratio'])}배 작았습니다"),
    ]
    fit_head = [("피팅 구간", 0), ("이동도 (cm²/V·s)", 1), ("문턱전압 (V)", 1), ("R²", 1)]
    fit_rows = lambda rs: [[span(r), num(r["mu"], 4), f"{r['vth']:.3f}", f"{r['r2']:.4f}"] for r in rs]

    items = [
        (f"<p>기존 도구의 3.0 판은 원자료의 전류를 절댓값으로 바꿔 옮겼습니다. 옮긴 뒤의 검사도 같은 변환을 거친 값끼리 "
         f"비교해서 통과했습니다. 원자료를 다시 세어 보면 그때 공개했던 9개 파일에 음수 전류가 {c1['total']}개, "
         f"음수가 있는 파일이 {c1['files_with_negative']}개입니다.</p>"
         + table([("파일", 0), ("측정점", 1), ("음수 전류", 1)],
                 [[f["name"], str(f["points"]), str(f["negative"])] for f in c1["files"]])
         + "<p class=note>3.0 판의 파일은 기존 저장소의 기록에 남아 있지 않습니다. 여기서 다시 확인한 것은 "
           "“원자료에 그런 부호가 그만큼 있다”까지이고, “3.0이 그 부호를 지웠다”는 기존 저장소의 변경 내역이 근거입니다.</p>"),
        (f"<p>기존 도구는 a-IGZO W20/L4에 피팅 구간 후보 3개를 냈습니다. 셋은 0.5 V씩 밀린 옆 구간이어서 이동도가 "
         f"{num(near[0]['mu'])} ~ {num(near[-1]['mu'])}로 비슷했고, 값이 안정적인 것처럼 보였습니다. "
         f"같은 파일을 겹치지 않는 2 V 구간으로 나누면 {num(lo['mu'])}에서 {num(hi['mu'])}까지 달라집니다.</p>"
         + "<h3>기존 도구의 후보 3개</h3>" + table(fit_head, fit_rows(near))
         + "<h3>겹치지 않는 2 V 구간</h3>" + table(fit_head, fit_rows(far))
         + f"<p class=note>겹치지 않는 구간의 R²는 모두 {r2_min:.4f} 이상입니다. 직선이 잘 맞는다는 것만으로는 "
           "어느 구간이 맞는지 가릴 수 없습니다.</p>"),
        (f"<p>포화 영역 식은 이동도가 전압과 무관하게 일정하다고 가정합니다. 세 재료를 같은 방법으로 훑으면 "
         f"a-IGZO는 계속 커지고, a-Si는 조금씩 커지고({num(asi_ok[0]['mu'])} → {num(asi_ok[-1]['mu'])}), "
         f"LTPS는 {span(ltps_top)}에서 {num(ltps_top['mu'])}까지 커졌다가 다시 작아집니다.</p>"
         + bars(asi, "그림 2. 구간별 포화 이동도", "a-Si W20/L4")
         + bars(ltps, "그림 3. 구간별 포화 이동도", "LTPS W10/L5")
         + "<h3>수업 자료의 예시 구간 15 ~ 20 V로 계산하면</h3>"
         + table([("파일", 0), ("실제로 쓴 점", 0), ("이동도 (cm²/V·s)", 1), ("R²", 1)],
                 [[r["name"], span(r), num(r["mu"]), f"{r['r2']:.4f}"] for r in c3["example"]])
         + "<p class=note>a-IGZO 측정은 18 V에서 끝나므로 예시 구간을 그대로 쓸 수 없습니다. LTPS는 음의 전압으로 켜지는 "
           "소자라 −15 ~ −20 V로 계산했습니다.</p>"),
        (f"<p>밴드갭은 빛을 흡수하기 시작하는 에너지(흡수단)에서 구합니다. UV–Vis 측정 파일 세 개는 모두 파장 "
         f"{uv['nm_min']:g} ~ {uv['nm_max']:g} nm, 광자 에너지로 {uv['ev_min']:.3f} ~ {uv['ev_max']:.3f} eV입니다. "
         f"결정질 실리콘의 밴드갭 약 {c4['si_gap_ev']} eV(교과서 값, 파장 약 {c4['si_gap_nm']:.0f} nm)는 이 범위 밖입니다. "
         f"기존 도구는 이 자료에서 Poly-Si의 밴드갭을 계산해 “안정”이라고 표시했습니다.</p>"
         + table([("파일", 0), ("측정점", 1), ("파장 (nm)", 1), ("광자 에너지 (eV)", 1)],
                 [[f["name"], str(f["points"]), f"{f['nm_min']:g} ~ {f['nm_max']:g}",
                   f"{f['ev_min']:.3f} ~ {f['ev_max']:.3f}"] for f in c4["files"]])),
        (f"<p>한 파일에는 같은 소자를 여러 조건으로 잰 측정이 들어 있습니다. a-IGZO 5개 파일에서 게이트 18 V일 때의 "
         f"전류를 두 측정에서 꺼내 나눴습니다. 드레인 전압이 더 높은 쪽 전류가 같거나 커야 하므로 비율이 1 이하여야 "
         f"정상인데, {odd['name']}만 {num(odd['ratio'])}입니다. 나머지 넷은 {num(min(rest))} ~ {num(max(rest))}입니다.</p>"
         + table([("파일", 0), ("드레인 10 V 전류 ÷ 드레인 18 V 전류", 1)],
                 [[f["name"], ("!" if f is odd else "") + num(f["ratio"])] for f in c5["files"]])
         + "<p class=note>원인은 알 수 없습니다. 여러 해 전에 측정된 자료라 측정 기록이 없습니다. 이 파일에서 나온 이동도는 "
           "믿을 수 없는 값으로 봅니다.</p>"),
    ]

    body = [f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TFT 피팅 구간 비교 도구</title>
<meta name="description" content="AI가 낸 TFT 분석 결과를 원자료로 다시 계산해, 사람이 직접 확인해야 할 것을 정리한 기록.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>{CSS}</style>
</head>
<body><div class=wrap>
<nav><b>TFT 피팅 구간 비교 도구</b><div><a href="#checklist">검수 기준표</a><a href="#recalc">다시 계산</a><a href="#log">AI 협업 기록</a><a href="#limits">한계</a><a href="{REPO_URL}">GitHub</a></div></nav>
<header>
<h1>AI가 낸 TFT 분석 결과를 원자료로 다시 계산해, 사람이 직접 확인해야 할 것을 정리한 기록.</h1>
<p class=sub>대학 실험 수업에서 “직선을 어디에 맞추느냐(피팅 구간)에 따라 값이 달라진다”는 의문이 남았습니다. AI와 분석 도구를 만들었고, AI가 낸 결과를 원자료로 다시 따져 AI에게 맡겨도 되는 일과 사람이 직접 확인해야 하는 일을 검수 기준표로 나눴습니다.</p>
</header>
<section class=hero>
<div>
<div class=sub>같은 측정 파일에서 피팅 구간만 바꾸면, 이동도가</div>
<div class=big>{c2['far_spread']:.1f}<span>배</span></div>
<div class=sub>달라집니다. 가장 큰 값 {num(hi['mu'])}({span(hi)})을 가장 작은 값 {num(lo['mu'])}({span(lo)})로 나눈 비율입니다.</div>
</div>
{bars(c3['sweeps']['IGZO2004.csv'], '그림 1. 구간별 포화 이동도', 'a-IGZO W20/L4')}
</section>
<section id=checklist>
<h2>검수 기준표</h2>
<p class=sub>AI가 낸 결과에서 사람이 직접 확인할 것 다섯 가지입니다. 오른쪽은 이 프로젝트에서 실제로 있었던 일입니다.</p>
<div class=scroll><table class=check><thead><tr><th scope=col>번호</th><th scope=col style="width:30%">직접 확인할 것</th><th scope=col>이 프로젝트에서 있었던 일</th><th scope=col style="width:144px">확인 상태</th></tr></thead><tbody>"""]
    for n, (what, happened) in enumerate(checklist, 1):
        body.append(f"<tr><td class=n style='text-align:left'>{n}</td><td><b>{what}</b></td>"
                    f"<td><a href='#case{n}' style='color:inherit;text-decoration:none'>{happened}</a></td><td>{state(n)}</td></tr>")
    body.append("""</tbody></table></div>
<p class=note>“직접 확인 전”은 AI가 계산했고 작성자가 아직 같은 명령을 직접 돌려 대조하지 않았다는 뜻입니다. 원자료는 수업에서 여러 해 동안 써 온 측정 파일이라 공개하지 않습니다.</p>
</section>
<section id=recalc>
<h2>다시 계산</h2>
<p class=sub>항목마다 있었던 일, 원자료에서 다시 계산하는 명령, 그 결과입니다. 아래 숫자는 모두 이 명령들의 출력에서 만들어졌습니다.</p>""")
    for n, ((what, _), html) in enumerate(zip(checklist, items), 1):
        body.append(f"<div class=item id=case{n}><h3>{n}. {what}</h3>{html}"
                    f"<p class=small>다시 계산하는 명령 <code>python -m recheck case {n}</code> &nbsp; {state(n)}</p></div>")
    body.append(f"""</section>
<section id=log>
<h2>AI 협업 기록</h2>
<p class=sub>코드는 AI(Claude)가 썼습니다. 작성자는 방향을 정하고, AI의 제안을 받아들이거나 거절했습니다. 단계마다 있었던 일을 그대로 적은 기록이 저장소의 <a href="{REPO_URL}/blob/main/docs/AI협업기록.md">docs/AI협업기록.md</a>에 있습니다.</p>
<h3>AI가 틀렸던 것과 찾아낸 방법</h3>
<ul>
<li>부탁한 구간이 측정 범위를 넘어도 아무 말 없이 잘린 범위로 계산했습니다. 15 ~ 20 V와 15 ~ 18 V의 결과가 똑같이 나와서 드러났고, 실제로 쓴 범위를 함께 출력하도록 고쳤습니다.</li>
<li>“몇 배”를 세는 규칙을 숫자를 보기 전에 정했는데, LTPS에서는 통하지 않았습니다. 꺼진 구간의 잡음이 규칙을 통과해 수백만 배라는 숫자가 나왔습니다. 결과를 본 뒤에 규칙을 고치지 않았고, LTPS는 배수 하나로 줄이지 않고 그림 3으로 보여 줍니다.</li>
<li>첫 화면 시안이 모든 내용을 똑같은 상자에 담아 위계가 없었습니다. 작성자가 보고 거절했습니다.</li>
<li>수업 자료를 열어 보지 않은 채 질문을 냈습니다. 작성자가 읽으라고 지시한 뒤에야 수업 자료에 피팅 구간을 고르는 기준이 없다는 것을 확인했습니다.</li>
</ul>
<h3>작성자가 거절하거나 바꾼 AI의 제안</h3>
<ul>
<li>“원자료 공개 허락을 받자”는 제안 대신, 원자료를 아예 올리지 않기로 했습니다.</li>
<li>기준표 후보 중 “절연막 용량 값의 출처”는 수업 진행을 위한 값이라 따지지 않기로 하고 뺐습니다.</li>
<li>AI가 추천한 이름 “다시 계산 노트”는 TFT가 들어가지 않아 거절했습니다.</li>
</ul>
</section>
<section id=limits>
<h2>한계</h2>
<ul>
<li>이 기록의 목적은 정확한 소자 값을 내는 것이 아닙니다. 분석에 쓴 TFT 파일 15개는 수업에서 여러 해 동안 써 온 측정 자료이고, 작성자가 직접 측정한 것이 아닙니다.</li>
<li>절연막 용량은 수업 실습에서 준 값 1.75×10⁻⁸ F/cm²을 세 재료에 똑같이 썼습니다. 이 값이 틀리면 이동도의 절대값은 같은 비율로 틀리지만, 구간에 따라 몇 배 달라지는가는 바뀌지 않습니다.</li>
<li>채널 폭과 길이는 파일 이름에서 읽었습니다(IGZO2004 → W 20, L 4 µm). 일부만 작성자가 확인했고 나머지는 가정입니다.</li>
<li>이동도 측정은 드레인과 게이트를 묶어 함께 올린 측정이라고 가정했습니다.</li>
<li>{c2['far_spread']:.1f}배는 a-IGZO W20/L4 한 파일을 2 V 구간으로 나눴을 때의 값입니다. 구간을 다르게 나누면 숫자가 달라집니다.</li>
<li>기준표의 확인 상태가 “직접 확인 전”인 항목은 AI의 계산만 거친 것입니다.</li>
</ul>
</section>
<footer>이 페이지는 <code>python -m recheck build</code> 한 번으로 다시 만들어집니다. 계산 결과 원본은 저장소의 <a href="{REPO_URL}/tree/main/results">results/</a>에 있습니다.</footer>
</div></body></html>
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
    (ROOT / "site" / "data.json").write_text(f"[\n{lines}\n]\n", encoding="utf-8", newline="\n")
    print("썼습니다: results/cases.json, results/sweep.json, site/index.html, site/data.json")
