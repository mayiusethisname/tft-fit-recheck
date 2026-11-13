"""구간 훑기와 검수 기준표 항목. 항목마다 함수 하나가 원자료에서 숫자를 다시 계산해 출력한다."""
from recheck import fit, read_raw


def sweep_file(path):
    """파일 하나를 2 V 구간으로 훑은 결과 목록."""
    _, w, l = read_raw.device(path)
    pts = read_raw.mobility_points(path)
    return [fit.saturation_fit(pts, w, l, a, b) for a, b in fit.windows(pts)]


def spread(results):
    """가장 큰 μ ÷ 가장 작은 μ. 구간이 2개보다 적으면 None."""
    mus = [r["mu"] for r in results]
    return max(mus) / min(mus) if len(mus) >= 2 else None


def mu_text(r):
    return f"{r['mu']:.3g}" if fit.turned_on(r) else "계산 안 함"


def print_rows(results):
    print(f"  {'구간 (V)':<12}{'μ (cm²/V·s)':>13}{'Vth (V)':>10}{'R²':>9}   Vth가 구간 앞에 있는가")
    for r in results:
        span = f"{r['used_from']:g} ~ {r['used_to']:g}"
        if fit.turned_on(r):
            ok = "예" if fit.vth_before_window(r) else "아니오"
            print(f"  {span:<14}{r['mu']:>12.4g}{r['vth']:>10.3f}{r['r2']:>9.4f}   {ok}")
        else:
            print(f"  {span:<14}{'계산 안 함':>8}{'':>10}{r['r2']:>9.4f}   (기울기가 0 이하)")


def sweep(name=None):
    """파일 이름을 주면 그 파일의 구간별 표, 안 주면 15개 파일 요약."""
    if name:
        print(f"{name}  2 V 구간별 결과")
        print_rows(sweep_file(read_raw.RAW_DIR / name))
        return
    print("2 V 구간별 이동도 (cm²/V·s). 구간은 0 V에서부터 구동 방향으로 센 것: 1번째 = 0~2 V, 10번째 = 18~20 V")
    print(f"{'파일':<14}" + "".join(f"{k:>9}" for k in range(1, 11)) + f"{'전체 배':>12}{'식에 맞는 구간만':>12}")
    for path in read_raw.raw_files():
        results = sweep_file(path)
        on = [r for r in results if fit.turned_on(r)]
        valid = [r for r in results if fit.vth_before_window(r)]
        cells = "".join(f"{mu_text(r) if fit.turned_on(r) else '-':>9}" for r in results).ljust(90)
        ratios = "".join(f"{s:>12.3g}" if s else f"{'-':>12}" for s in (spread(on), spread(valid)))
        print(f"{path.name:<16}{cells}{ratios}")
    print("'-' = 계산 안 함 (기울기가 0 이하).  전체 배 = 계산한 구간 중 가장 큰 μ ÷ 가장 작은 μ.")
    print("식에 맞는 구간만 = 그 구간에서 나온 Vth가 구간 시작점보다 앞에 있는 구간끼리만 비교.")


def case2():
    """2번. AI가 낸 '여러 후보'가 정말 서로 다른가."""
    path = read_raw.RAW_DIR / "IGZO2004.csv"
    _, w, l = read_raw.device(path)
    pts = read_raw.mobility_points(path)
    print("기준표 2번: 기존 도구가 IGZO2004에 낸 후보 구간 3개 (알려진 문제 있음: 0.5 V씩 밀린 옆 구간)")
    near = [fit.saturation_fit(pts, w, l, a, b) for a, b in ((5, 9), (5.5, 9.5), (6, 10))]
    print_rows(near)
    print(f"  후보 3개 사이의 차이: {spread(near):.3g}배")
    print("같은 파일을 겹치지 않는 2 V 구간으로 나눈 결과")
    far = [r for r in sweep_file(path) if fit.vth_before_window(r)]
    print_rows(far)
    print(f"  겹치지 않는 구간 사이의 차이: {spread(far):.3g}배")


def case3():
    """3번. 계산식이 성립하는 조건인가 (식은 μ가 전압과 무관하게 일정하다고 가정한다)."""
    print("기준표 3번: 세 재료의 W20/L4·W10/L5 소자를 2 V 구간으로 훑은 결과")
    for name in ("IGZO2004.csv", "aSi2004.DAT", "LTPS1005.DAT"):
        sweep(name)
    print("수업 자료의 예시 구간 15 ~ 20 V (LTPS는 −15 ~ −20 V)")
    for name in ("IGZO2004.csv", "aSi2004.DAT", "LTPS1005.DAT"):
        path = read_raw.RAW_DIR / name
        _, w, l = read_raw.device(path)
        sign = -1 if name.startswith("LTPS") else 1
        r = fit.saturation_fit(read_raw.mobility_points(path), w, l, sign * 15, sign * 20)
        print(f"  {name:<14} 실제로 쓴 점 {r['used_from']:g} ~ {r['used_to']:g} V   μ = {mu_text(r)}   Vth = {r['vth']:.3f} V   R² = {r['r2']:.4f}")


CASES = {"2": case2, "3": case3}
