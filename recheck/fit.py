"""한 피팅 구간에서 포화 이동도와 문턱전압을 구한다.

수업 자료(8주차 9쪽)의 포화 영역 식:
    I = μ · C · (W / 2L) · (V − Vth)²
양변에 제곱근을 씌우면 직선이 된다:
    √|I| = a · V + b
직선의 기울기 a와 절편 b에서:
    μ   = 2 · L · a² / (C · W)
    Vth = −b / a
"""
from math import sqrt

# 절연막 용량 (F/cm²). 수업 실습 스크립트의 값을 세 재료에 그대로 쓴다 (가정, docs/설계.md 3절).
C_OX = 1.75e-8


def line_fit(xs, ys):
    """점들에 가장 잘 맞는 직선 y = a·x + b 를 구한다 (최소제곱법).

    돌려주는 값: 기울기 a, 절편 b, R²(1에 가까울수록 점들이 직선에 가깝다).
    """
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    syy = sum((y - mean_y) ** 2 for y in ys)
    a = sxy / sxx
    b = mean_y - a * mean_x
    r2 = sxy * sxy / (sxx * syy) if syy else 1.0
    return a, b, r2


def saturation_fit(points, w, l, v_from, v_to):
    """전압이 v_from과 v_to 사이(양끝 포함)인 점들로 μ와 Vth를 구한다.

    points: (전압 V, 전류 A) 목록.  w, l: 채널 폭과 길이 (같은 단위면 된다. 비율만 쓴다).
    음의 전압으로 켜지는 소자(LTPS)도 원래 전압 축 그대로 넣는다. 기울기가 음수가 될 뿐
    a²과 −b/a는 그대로 성립한다.
    """
    lo, hi = min(v_from, v_to) - 1e-9, max(v_from, v_to) + 1e-9
    chosen = [(v, sqrt(abs(i))) for v, i in points if lo <= v <= hi]
    if len(chosen) < 3:
        raise ValueError(f"구간 {v_from}~{v_to} V 안의 점이 {len(chosen)}개뿐입니다")
    a, b, r2 = line_fit([v for v, _ in chosen], [s for _, s in chosen])
    return {
        "v_from": v_from,
        "v_to": v_to,
        # 실제로 쓴 점의 전압 범위. 부탁한 구간이 측정 범위를 넘으면 이 값이 더 좁다.
        "used_from": min(v for v, _ in chosen),
        "used_to": max(v for v, _ in chosen),
        "points": len(chosen),
        "slope": a,
        "intercept": b,
        "r2": r2,
        "mu": 2 * l * a * a / (C_OX * w),  # cm²/V·s
        "vth": -b / a,  # V
    }
