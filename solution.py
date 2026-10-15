#!/usr/bin/env python3
"""
안내서비스.csv 카테고리별 자동 분리·집계 도구
- 입력 : 안내서비스.csv (스크립트와 같은 폴더)
- 처리 : 카테고리별로 행을 분리 → 출력_카테고리별/<카테고리명>.csv
- 출력 : 카테고리별 건수·대표 문의기관 집계 → 결과_카테고리집계.csv + 콘솔 출력
표준 라이브러리(csv · pathlib · collections)만 사용합니다.
실행: python solution.py   (다른 파일을 쓰려면 python solution.py 다른파일.csv)
"""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
INPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "안내서비스.csv"
OUT_DIR = BASE / "출력_카테고리별"
SUMMARY = BASE / "결과_카테고리집계.csv"
CAT_COL, ORG_COL = "카테고리", "문의기관"


def read_rows(path: Path):
    """UTF-8(BOM 포함) 우선, 실패하면 CP949(엑셀 저장본)로 읽는다."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            with path.open(encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                fields = [h.strip() for h in reader.fieldnames or []]
                rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in reader]
            return fields, [r for r in rows if any(r.values())]  # 빈 줄 제거
        except UnicodeDecodeError:
            continue
    sys.exit(f"[ERROR] 인코딩을 읽을 수 없습니다: {path}")


def safe_filename(name: str) -> str:
    bad = '\\/:*?"<>|'
    cleaned = "".join("_" if ch in bad else ch for ch in name).strip()
    return cleaned or "미분류"


def main():
    if not INPUT.exists():
        sys.exit(f"[ERROR] 입력 파일이 없습니다: {INPUT}")
    fields, rows = read_rows(INPUT)
    missing = [c for c in (CAT_COL, ORG_COL) if c not in fields]
    if missing:
        sys.exit(f"[ERROR] 필수 열이 없습니다: {missing} (현재 열: {fields})")

    # 1) 카테고리별 분리 (원본 등장 순서 유지)
    groups = defaultdict(list)
    for r in rows:
        groups[r[CAT_COL] or "미분류"].append(r)

    OUT_DIR.mkdir(exist_ok=True)
    for cat, items in groups.items():
        with (OUT_DIR / f"{safe_filename(cat)}.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(items)

    # 2) 집계: 건수 많은 순, 같으면 카테고리명 순
    order = sorted(groups, key=lambda c: (-len(groups[c]), c))
    total = len(rows)
    table = []
    for cat in order:
        items = groups[cat]
        orgs = Counter(r[ORG_COL] for r in items)          # 동률이면 먼저 나온 기관
        top_org, top_n = orgs.most_common(1)[0]
        table.append([cat, len(items), round(len(items) / total * 100, 1),
                      top_org, top_n, len(orgs),
                      " / ".join(f"{o}({n})" for o, n in orgs.most_common())])
    table.append(["합계", total, 100.0, "", "", len({r[ORG_COL] for r in rows}), ""])

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:  # 엑셀에서 한글 안 깨짐
        w = csv.writer(f)
        w.writerow(["카테고리", "건수", "비율(%)", "대표문의기관", "대표기관건수", "문의기관수", "문의기관별건수"])
        w.writerows(table)

    # 3) 콘솔 출력
    print(f"[OK] 안내서비스 {total}건 카테고리별 분리 → {OUT_DIR.name}/ ({len(groups)}개 파일)")
    for cat, n, pct, org, *_ in table[:-1]:
        print(f"  · {cat} {n}건 ({pct}%) · 대표 문의기관: {org}")
    print(f"[OK] 집계표 → {SUMMARY.name}")


if __name__ == "__main__":
    main()
