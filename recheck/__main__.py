"""명령 창구.

    python -m recheck files                      원자료 15개 요약
    python -m recheck fit IGZO2004.csv 5.5 9.5   한 구간의 이동도와 문턱전압
    python -m recheck sweep                      15개 파일을 2 V 구간으로 훑은 요약
    python -m recheck sweep IGZO2004.csv         파일 하나의 구간별 표
    python -m recheck case 2                     검수 기준표 2번 (1~5번)
"""
import sys

from recheck import cases, fit, read_raw


def files():
    """원자료 15개의 MOBILITY 측정을 한 줄씩 요약한다."""
    print(f"{'파일':<14}{'재료':<6}{'W':>3}{'L':>4}{'점 수':>6}  {'첫 줄 (V, A)':<26}{'끝 줄 (V, A)':<26}{'음수 전류':>8}")
    for path in read_raw.raw_files():
        material, w, l = read_raw.device(path)
        pts = read_raw.mobility_points(path)
        negative = sum(1 for _, i in pts if i < 0)
        first = f"{pts[0][0]:g}, {pts[0][1]:g}"
        last = f"{pts[-1][0]:g}, {pts[-1][1]:g}"
        print(f"{path.name:<16}{material:<8}{w:>3}{l:>4}{len(pts):>8}  {first:<28}{last:<28}{negative:>8}")


def fit_one(name, v_from, v_to):
    """파일 하나, 구간 하나의 결과를 출력한다."""
    path = read_raw.RAW_DIR / name
    _, w, l = read_raw.device(path)
    r = fit.saturation_fit(read_raw.mobility_points(path), w, l, float(v_from), float(v_to))
    print(f"{name}  W {w} / L {l}  구간 {r['v_from']:g} ~ {r['v_to']:g} V  "
          f"(실제로 쓴 점 {r['used_from']:g} ~ {r['used_to']:g} V, {r['points']}점)")
    print(f"  기울기 a = {r['slope']:.6e}   절편 b = {r['intercept']:.6e}   R² = {r['r2']:.4f}")
    print(f"  이동도 μ = {r['mu']:.4g} cm²/V·s   문턱전압 Vth = {r['vth']:.4g} V")


if __name__ == "__main__":
    commands = {"files": files, "fit": fit_one, "sweep": cases.sweep, "case": lambda n: cases.CASES[n]()}
    try:
        commands[sys.argv[1]](*sys.argv[2:])
    except (IndexError, KeyError, TypeError):
        sys.exit(__doc__)
