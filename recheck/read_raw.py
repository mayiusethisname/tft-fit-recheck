"""원자료 파일을 읽는다. 숫자는 바꾸지 않는다(부호 그대로).

원자료 한 파일에는 측정이 여러 개 들어 있고, 측정마다
    DATA:  MOBILITY  04/08/2020  13:50:05
같은 줄로 시작한다. 그 아래에 빈 줄, 열 이름 줄, 숫자 줄들이 온다.
DAT 파일은 칸을 탭으로, CSV 파일은 쉼표로 나눈다.
"""
import re
from pathlib import Path

# 원자료는 이 PC에만 있다. 레포에는 올리지 않는다 (docs/adr/0001).
RAW_DIR = Path(r"D:\AMD\8주차\TFT DATA")


def to_number(cell):
    """칸 하나를 숫자로 바꾼다. '*'나 빈칸처럼 숫자가 아니면 None."""
    try:
        return float(cell)
    except ValueError:
        return None


def read_section(path, name):
    """파일에서 이름이 name인 측정을 찾아 (열 이름 목록, 행 목록)을 돌려준다.

    행 하나는 {열 이름: 숫자 또는 None} 사전이다.
    """
    path = Path(path)
    sep = "," if path.suffix.lower() == ".csv" else "\t"
    header, rows, inside = None, [], False
    for line in path.read_text(encoding="ascii").splitlines():
        if line.startswith("DATA:"):
            if inside:
                break  # 다음 측정이 시작되면 끝
            inside = line.replace(",", " ").split()[1] == name
            continue
        if not inside:
            continue
        cells = [c.strip() for c in line.split(sep)]
        if not any(cells):
            continue  # 빈 줄
        if header is None:
            header = [c for c in cells if c]
            continue
        rows.append({h: to_number(c) for h, c in zip(header, cells)})
    if header is None:
        raise ValueError(f"{path.name}: {name} 측정을 찾지 못했습니다")
    return header, rows


def mobility_points(path):
    """MOBILITY 측정의 (전압, 전류) 목록. 원자료의 순서와 부호 그대로."""
    _, rows = read_section(path, "MOBILITY")
    points = []
    for n, row in enumerate(rows, start=1):
        v, i = row.get("VD"), row.get("ID")
        if v is None or i is None:
            # 못 읽은 숫자를 건너뛰거나 채우지 않는다. 멈추고 알린다.
            raise ValueError(f"{Path(path).name}: MOBILITY {n}번째 줄의 VD 또는 ID를 읽지 못했습니다")
        points.append((v, i))
    return points


def device(path):
    """파일 이름에서 (재료, 채널 폭 W, 채널 길이 L)을 읽는다. 단위 µm.

    가정: 이름 끝의 네 자리가 W 두 자리 + L 두 자리다. 예: IGZO2004 -> W 20, L 4.
    """
    m = re.fullmatch(r"([A-Za-z]+)(\d\d)(\d\d)", Path(path).stem)
    if not m:
        raise ValueError(f"{Path(path).name}: 이름에서 W와 L을 읽지 못했습니다")
    return m.group(1), int(m.group(2)), int(m.group(3))


def raw_files():
    """분석할 원자료 15개 (DAT와 CSV). JNB 같은 다른 형식은 뺀다."""
    return sorted(p for p in RAW_DIR.iterdir() if p.suffix.lower() in (".dat", ".csv"))
