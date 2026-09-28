"""월별 자동차 등록현황 엑셀을 대시보드용 통합 CSV로 변환한다.

실행:
    python csv_from_excel.py
시험:
    python csv_from_excel.py --limit 1

원본 엑셀의 시트명·머리글이 연도에 따라 조금씩 다르므로, 이 프로그램은
시트 이름과 '시도/시군구/계' 머리글을 유연하게 탐색한다. 변환되지 않은
파일은 오류로 덮어쓰지 않고 목록으로 알려 준다.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = PROJECT_DIR / "data"
DEFAULT_OUTPUT = DEFAULT_INPUT_DIR / "자동차_등록현황_통합.csv"
DEFAULT_VERIFIED_OUTPUT = DEFAULT_INPUT_DIR / "자동차_등록현황_통합_검증.csv"
COLUMNS = ["기준년월", "시도", "시군구", "용도", "연료", "성별", "연령대", "규모", "등록대수"]

SHEET_ALIASES = {
    "sigungu": ["통계표_시군구", "시군구별 등록현황", "시군구"],
    "usage": ["용도별 등록현황", "용도별_등록현황", "용도별"],
    "fuel": ["연료별 등록현황", "연료별_등록현황", "연료별"],
    "gender": ["성별,연령별", "성별_연령별", "성별 및 연령별", "성별연령별"],
    "size": ["차종별_규모별 등록현황", "차종별 규모별 등록현황", "규모별 등록현황", "규모별"],
}


def clean(value: object, default: str = "전체") -> str:
    """셀 값을 공백 하나의 문자열로 바꾸고 빈 값은 기본값으로 채운다."""
    if pd.isna(value):
        return default
    value = re.sub(r"\s+", " ", str(value)).strip()
    return value or default


def normalized(value: object) -> str:
    """시트명·머리글 비교용으로 공백, 번호, 특수문자 차이를 줄인다."""
    return re.sub(r"[^가-힣A-Za-z0-9]", "", clean(value, "")).lower()


def period_from_filename(path: Path) -> str | None:
    matched = re.search(r"(20\d{2})년\s*(1[0-2]|0?[1-9])월", path.stem)
    if not matched:
        return None
    return f"{matched.group(1)}-{int(matched.group(2)):02d}"


def normalize_age(value: object) -> str:
    value = clean(value)
    aliases = {"10대이하": "10대 이하", "90대이상": "90대 이상", "합": "계"}
    return aliases.get(re.sub(r"\s+", "", value), value)


def find_sheet(book: pd.ExcelFile, aliases: list[str]) -> str | None:
    """정확한 이름이 없을 때도 공백·번호 차이를 무시해 가장 가까운 시트를 찾는다."""
    wanted = [normalized(alias) for alias in aliases]
    for name in book.sheet_names:
        name_key = normalized(name)
        if any(alias == name_key or alias in name_key or name_key in alias for alias in wanted):
            return name
    return None


def read_table(path: Path, sheet_name: str) -> pd.DataFrame:
    """머리글이 2~4행에 있는 통계표를 읽어 단일 문자열 컬럼명으로 만든다."""
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    header_row = None
    for index in range(min(12, len(raw))):
        text = " ".join(normalized(cell) for cell in raw.iloc[index].tolist())
        if "시도" in text or "시군구" in text:
            header_row = index
            break
    if header_row is None:
        raise ValueError("시도 또는 시군구 머리글 행을 찾지 못했습니다")

    # 다단 머리글은 아래 행의 항목명(예: 계)을 함께 붙인다.
    upper = raw.iloc[header_row].tolist()
    lower = raw.iloc[header_row + 1].tolist() if header_row + 1 < len(raw) else []
    names: list[str] = []
    for position, value in enumerate(upper):
        first = clean(value, "")
        second = clean(lower[position], "") if position < len(lower) else ""
        if second and second not in {"nan", "Unnamed: 0"} and second != first:
            names.append(f"{first} {second}".strip())
        else:
            names.append(first or f"열{position}")
    table = raw.iloc[header_row + 1 :].copy()
    table.columns = names
    return table.dropna(how="all")


def find_column(columns: list[str], candidates: list[str]) -> str | None:
    keys = [normalized(candidate) for candidate in candidates]
    for column in columns:
        column_key = normalized(column)
        if any(key == column_key or key in column_key for key in keys):
            return column
    return None


def find_total_column(columns: list[str], excluded: set[str]) -> str | None:
    """'계'·'합계'·'총계' 열을 우선 사용한다. 없으면 '등록대수' 열을 찾는다."""
    for column in columns:
        if column in excluded:
            continue
        key = normalized(column)
        if key in {"계", "합계", "총계"} or key.endswith("계"):
            return column
    return find_column(columns, ["등록대수", "대수"])


def number(value: object) -> int | None:
    value = clean(value, "")
    if not value or value in {"-", "nan"}:
        return None
    value = re.sub(r"[^0-9.-]", "", value)
    try:
        return int(float(value))
    except ValueError:
        return None


def base_row(period: str, sido: object = "전체") -> dict[str, object]:
    return {"기준년월": period, "시도": clean(sido), "시군구": "전체", "용도": "전체", "연료": "전체", "성별": "전체", "연령대": "전체", "규모": "전체"}


def valid_sido(value: object) -> bool:
    return clean(value) not in {"전체", "계", "합계", "총계", "시도"}


def parse_sigungu(path: Path, sheet: str, period: str) -> list[dict[str, object]]:
    table = read_table(path, sheet)
    columns = list(table.columns)
    sido_col = find_column(columns, ["시도"])
    sigungu_col = find_column(columns, ["시군구", "시군구별"])
    total_col = find_total_column(columns, {sido_col or "", sigungu_col or ""})
    if not sido_col or not sigungu_col or not total_col:
        raise ValueError("시도·시군구·계 열을 찾지 못했습니다")
    rows: list[dict[str, object]] = []
    last_sido = ""
    for _, source in table.iterrows():
        sido = clean(source[sido_col], "")
        if valid_sido(sido):
            last_sido = sido
        sigungu = clean(source[sigungu_col], "")
        count = number(source[total_col])
        if not last_sido or not sigungu or sigungu in {"계", "합계", "총계", "시군구"} or count is None:
            continue
        row = base_row(period, last_sido)
        row["시군구"] = re.sub(r"구$", "", sigungu) if last_sido in {"서울", "부산", "대구", "인천", "광주", "대전", "울산"} else sigungu
        row["등록대수"] = count
        rows.append(row)
    return rows


def parse_dimension(path: Path, sheet: str, period: str, dimension: str) -> list[dict[str, object]]:
    """용도·연료·성별/연령·규모 시트에서 각 분류의 '계' 값을 뽑는다."""
    table = read_table(path, sheet)
    columns = list(table.columns)
    sido_col = find_column(columns, ["시도"])
    category_candidates = {
        "usage": ["용도"], "fuel": ["연료"], "gender": ["성별"], "size": ["규모", "차종"],
    }
    output_column = {"usage": "용도", "fuel": "연료", "gender": "성별", "size": "규모"}[dimension]
    category_col = find_column(columns, category_candidates[dimension])
    age_col = find_column(columns, ["연령"] if dimension == "gender" else [])
    total_col = find_total_column(columns, {item for item in [sido_col, category_col, age_col] if item})
    if not category_col or not total_col:
        raise ValueError(f"{dimension}·계 열을 찾지 못했습니다")

    rows: list[dict[str, object]] = []
    last_sido = "전체"
    for _, source in table.iterrows():
        if sido_col:
            candidate = clean(source[sido_col], "")
            if valid_sido(candidate):
                last_sido = candidate
        category = clean(source[category_col], "")
        count = number(source[total_col])
        if not category or category in {"계", "합계", "총계", dimension} or count is None:
            continue
        row = base_row(period, last_sido)
        row[output_column] = normalize_age(category) if dimension == "gender" else category
        if dimension == "gender" and age_col:
            age = normalize_age(source[age_col])
            if age not in {"전체", "연령", "계"}:
                row["연령대"] = age
        row["등록대수"] = count
        rows.append(row)
    return rows


def parse_workbook(path: Path) -> tuple[list[dict[str, object]], list[str]]:
    period = period_from_filename(path)
    if period is None:
        return [], [f"{path.name}: 파일명에서 기준년월을 읽지 못함"]
    book = pd.ExcelFile(path)
    rows: list[dict[str, object]] = []
    messages: list[str] = []
    for kind, aliases in SHEET_ALIASES.items():
        sheet = find_sheet(book, aliases)
        if sheet is None:
            messages.append(f"{path.name}: {kind} 시트 없음")
            continue
        try:
            parsed = parse_sigungu(path, sheet, period) if kind == "sigungu" else parse_dimension(path, sheet, period, kind)
            rows.extend(parsed)
        except Exception as error:
            messages.append(f"{path.name}: {sheet} 처리 실패 ({error})")
    return rows, messages


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verified-output", type=Path, default=DEFAULT_VERIFIED_OUTPUT)
    parser.add_argument("--limit", type=int, default=None, help="시험할 엑셀 파일 수")
    args = parser.parse_args()

    files = sorted(path for path in args.input_dir.glob("*.xlsx") if not path.name.startswith("~$"))
    if args.limit is not None:
        files = files[: args.limit]
    if not files:
        print("변환할 xlsx 파일이 없습니다. 먼저 python car_dashboard.py를 실행하세요.")
        return

    all_rows: list[dict[str, object]] = []
    notices: list[str] = []
    for index, path in enumerate(files, start=1):
        print(f"[{index}/{len(files)}] 처리 중: {path.name}")
        rows, messages = parse_workbook(path)
        all_rows.extend(rows)
        notices.extend(messages)
    if not all_rows:
        raise RuntimeError("변환된 행이 없습니다. 첫 엑셀의 시트 이름과 머리글을 확인하세요.")

    combined = pd.DataFrame(all_rows).reindex(columns=COLUMNS)
    combined["등록대수"] = pd.to_numeric(combined["등록대수"], errors="coerce")
    combined = combined.dropna(subset=["등록대수"]).copy()
    combined["등록대수"] = combined["등록대수"].astype("int64")
    combined = combined.drop_duplicates(subset=COLUMNS[:-1], keep="last").sort_values(COLUMNS[:-1])
    for output in [args.output, args.verified_output]:
        output.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(output, index=False, encoding="utf-8-sig")
        print(f"저장: {output} ({len(combined):,}행)")
    if notices:
        print("\n확인할 항목:")
        print("\n".join(notices))


if __name__ == "__main__":
    main()
