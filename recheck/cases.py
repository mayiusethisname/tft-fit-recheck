"""구간 훑기와 검수 기준표 항목.

항목마다 `caseN_data()`가 원자료에서 숫자를 다시 계산해 돌려주고, `caseN()`이 그것을 표로 출력한다.
사이트(build.py)도 같은 `caseN_data()`를 쓴다. 그래서 화면의 숫자와 명령의 출력이 같은 곳에서 나온다.
"""
from recheck import fit, read_raw

# UV–Vis 원자료 (7주차 실험). 이것도 레포에 올리지 않는다.
UV_DIR = read_raw.RAW_DIR.parent / "7주차"
PUBLISHED_BY_OLD_TOOL = ("aSi2002.DAT", "aSi2006.DAT", "aSi2020.DAT", "IGZO2002.csv", "IGZO2004.csv",
                         "IGZO2010.csv", "LTPS1002.DAT", "LTPS1005.DAT", "LTPS1010.DAT")
THREE_MATERIALS = ("IGZO2004.csv", "aSi2004.DAT", "LTPS1005.DAT")


def one_fit(name, v_from, v_to):
    """파일 하나, 구간 하나의 결과에 두 가지 판정(on, valid)을 붙여 돌려준다."""
    path = read_raw.RAW_DIR / name
    _, w, l = read_raw.device(path)
    r = fit.saturation_fit(read_raw.mobility_points(path), w, l, v_from, v_to)
    return dict(r, on=fit.turned_on(r), valid=fit.vth_before_window(r))


def sweep_file(name):
    """파일 하나를 2 V 구간으로 훑은 결과 목록."""
    pts = read_raw.mobility_points(read_raw.RAW_DIR / name)
    return [one_fit(name, a, b) for a, b in fit.windows(pts)]


def spread(results):
    """가장 큰 μ ÷ 가장 작은 μ. 구간이 2개보다 적으면 None."""
    mus = [r["mu"] for r in results]
    return max(mus) / min(mus) if len(mus) >= 2 else None


def print_rows(results):
    print(f"  {'구간 (V)':<12}{'μ (cm²/V·s)':>13}{'Vth (V)':>10}{'R²':>9}   Vth가 구간 앞에 있는가")
    for r in results:
        span = f"{r['used_from']:g} ~ {r['used_to']:g}"
        if r["on"]:
            print(f"  {span:<14}{r['mu']:>12.4g}{r['vth']:>10.3f}{r['r2']:>9.4f}   {'예' if r['valid'] else '아니오'}")
        else:
            print(f"  {span:<14}{'계산 안 함':>8}{'':>10}{r['r2']:>9.4f}   (기울기가 0 이하)")


def sweep(name=None):
    """파일 이름을 주면 그 파일의 구간별 표, 안 주면 15개 파일 요약."""
    if name:
        print(f"{name}  2 V 구간별 결과")
        print_rows(sweep_file(name))
        return
    print("2 V 구간별 이동도 (cm²/V·s). 구간은 0 V에서부터 구동 방향으로 센 것: 1번째 = 0~2 V, 10번째 = 18~20 V")
    print(f"{'파일':<14}" + "".join(f"{k:>9}" for k in range(1, 11)) + f"{'전체 배':>12}{'식에 맞는 구간만':>12}")
    for path in read_raw.raw_files():
        results = sweep_file(path.name)
        cells = "".join(f"{r['mu']:>9.3g}" if r["on"] else f"{'-':>9}" for r in results).ljust(90)
        both = (spread([r for r in results if r["on"]]), spread([r for r in results if r["valid"]]))
        print(f"{path.name:<16}{cells}" + "".join(f"{s:>12.3g}" if s else f"{'-':>12}" for s in both))
    print("'-' = 계산 안 함 (기울기가 0 이하).  전체 배 = 계산한 구간 중 가장 큰 μ ÷ 가장 작은 μ.")
    print("식에 맞는 구간만 = 그 구간에서 나온 Vth가 구간 시작점보다 앞에 있는 구간끼리만 비교.")


def case1_data():
    """1번. 숫자가 원자료 그대로 옮겨졌는가."""
    files = []
    for name in PUBLISHED_BY_OLD_TOOL:
        pts = read_raw.mobility_points(read_raw.RAW_DIR / name)
        files.append({"name": name, "points": len(pts), "negative": sum(1 for _, i in pts if i < 0)})
    return {"files": files, "total": sum(f["negative"] for f in files),
            "files_with_negative": sum(1 for f in files if f["negative"])}


def case1():
    d = case1_data()
    print("기준표 1번: 기존 도구가 공개했던 9개 파일의 원자료(MOBILITY)에 있는 음수 전류 개수")
    print("(기존 도구 3.0은 전류를 절댓값으로 옮겨 이 부호들을 지웠다. 3.0 파일 자체는 남아 있지 않다)")
    for f in d["files"]:
        print(f"  {f['name']:<14} {f['points']}점 중 음수 {f['negative']:>3}개")
    print(f"  합계: 음수 전류 {d['total']}개, 음수가 있는 파일 {d['files_with_negative']}개")


def case2_data():
    """2번. AI가 낸 '여러 후보'가 정말 서로 다른가."""
    near = [one_fit("IGZO2004.csv", a, b) for a, b in ((5, 9), (5.5, 9.5), (6, 10))]
    far = [r for r in sweep_file("IGZO2004.csv") if r["valid"]]
    return {"near": near, "near_spread": spread(near), "far": far, "far_spread": spread(far)}


def case2():
    d = case2_data()
    print("기준표 2번: 기존 도구가 IGZO2004에 낸 후보 구간 3개 (알려진 문제 있음: 0.5 V씩 밀린 옆 구간)")
    print_rows(d["near"])
    print(f"  후보 3개 사이의 차이: {d['near_spread']:.3g}배")
    print("같은 파일을 겹치지 않는 2 V 구간으로 나눈 결과")
    print_rows(d["far"])
    print(f"  겹치지 않는 구간 사이의 차이: {d['far_spread']:.3g}배")


def case3_data():
    """3번. 계산식이 성립하는 조건인가 (식은 μ가 전압과 무관하게 일정하다고 가정한다)."""
    example = []
    for name in THREE_MATERIALS:
        sign = -1 if name.startswith("LTPS") else 1
        example.append(dict(one_fit(name, sign * 15, sign * 20), name=name))
    return {"sweeps": {name: sweep_file(name) for name in THREE_MATERIALS}, "example": example}


def case3():
    d = case3_data()
    print("기준표 3번: 세 재료의 W20/L4·W10/L5 소자를 2 V 구간으로 훑은 결과")
    for name, results in d["sweeps"].items():
        print(f"{name}  2 V 구간별 결과")
        print_rows(results)
    print("수업 자료의 예시 구간 15 ~ 20 V (LTPS는 −15 ~ −20 V)")
    for r in d["example"]:
        print(f"  {r['name']:<14} 실제로 쓴 점 {r['used_from']:g} ~ {r['used_to']:g} V   "
              f"μ = {r['mu']:.3g}   Vth = {r['vth']:.3f} V   R² = {r['r2']:.4f}")


def case4_data():
    """4번. 이 자료로 구할 수 있는 값인가."""
    files = []
    for name in ("a-IGZO.csv", "a-Si.csv", "poly-Si.csv"):
        lines = (UV_DIR / name).read_text(encoding="ascii", errors="replace").splitlines()
        waves = []
        for line in lines[lines.index("XYDATA") + 1:]:
            if not line.strip():
                break  # 숫자 줄이 끝나면 멈춘다
            waves.append(float(line.split(",")[0]))
        lo, hi = min(waves), max(waves)
        files.append({"name": name, "points": len(waves), "nm_min": lo, "nm_max": hi,
                      "ev_min": 1239.84 / hi, "ev_max": 1239.84 / lo})
    return {"files": files, "si_gap_ev": 1.1, "si_gap_nm": 1239.84 / 1.1}


def case4():
    d = case4_data()
    print("기준표 4번: UV–Vis 파일의 측정 파장 범위를 광자 에너지로 바꾼 것 (E[eV] = 1239.84 / 파장[nm])")
    for f in d["files"]:
        print(f"  {f['name']:<12} {f['points']}점   파장 {f['nm_min']:g} ~ {f['nm_max']:g} nm   "
              f"에너지 {f['ev_min']:.3f} ~ {f['ev_max']:.3f} eV")
    print(f"  결정질 실리콘의 밴드갭은 약 {d['si_gap_ev']} eV (파장으로 약 {d['si_gap_nm']:.0f} nm, 교과서 값). 위 범위에 들어 있는지 본다.")


def case5_data():
    """5번. 같은 파일 안의 다른 측정과 맞는가."""
    files = []
    for path in read_raw.raw_files():
        if read_raw.device(path)[0] != "IGZO":
            continue
        _, rows = read_raw.read_section(path, "HIGHTRANS")
        row = next(r for r in rows if r["VG"] == 18)
        assert row["VD2"] == 10, "HIGHTRANS의 두 번째 드레인 전압이 10 V가 아니다"
        mob = dict(read_raw.mobility_points(path))[18]
        files.append({"name": path.name, "hightrans": row["ID2"], "mobility": mob, "ratio": row["ID2"] / mob})
    return {"files": files}


def case5():
    print("기준표 5번: a-IGZO 5개 파일에서 게이트 18 V일 때의 전류를 두 측정에서 나란히")
    print(f"  {'파일':<14}{'HIGHTRANS (드레인 10 V)':>20}{'MOBILITY (드레인 18 V)':>22}{'앞 ÷ 뒤':>10}")
    for f in case5_data()["files"]:
        print(f"  {f['name']:<14}{f['hightrans']:>22.3e}{f['mobility']:>22.3e}{f['ratio']:>12.3g}")
    print("  드레인 전압이 더 높은 MOBILITY 쪽 전류가 같거나 커야 정상이다 (앞 ÷ 뒤 가 1 이하).")
    print("  가정: MOBILITY는 드레인과 게이트를 묶어 함께 올린 측정이다 (열 이름은 VD 하나뿐).")


CASES = {"1": case1, "2": case2, "3": case3, "4": case4, "5": case5}
