"""국토교통 통계누리에서 월별 자동차 등록현황 엑셀을 내려받는다.

실행:
    python car_dashboard.py

같은 파일명이 data 폴더에 이미 있으면 다시 받지 않는다. 새 월 자료만
자동으로 추가되는 방식이므로 작업 스케줄러에서 실행해도 안전하다.
"""

from pathlib import Path
import re
import time

import requests
from bs4 import BeautifulSoup


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
LIST_URL = "https://stat.molit.go.kr/portal/cate/statMetaView.do?hFormId=1244&hRsId=58"
DOWNLOAD_URL = "https://stat.molit.go.kr/portal/common/downLoadFile.do"

# None이면 목록의 모든 월을 확인한다. 시험할 때만 1, 2처럼 바꾼다.
DOWNLOAD_COUNT = None
REQUEST_DELAY_SECONDS = 0.5


def get_file_information(onclick: str) -> dict[str, str] | None:
    """downFile('원본명','저장명','경로','프레임') 호출에서 필요한 값을 꺼낸다."""
    pattern = r"downFile\(\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'[^']*'\s*\)"
    matched = re.search(pattern, onclick or "")
    if not matched:
        return None
    return {
        "original_file_name": matched.group(1),
        "saved_file_name": matched.group(2),
        "midpath": matched.group(3),
    }


def find_vehicle_files(session: requests.Session) -> list[dict[str, str]]:
    """통계누리 목록 HTML에서 자동차 등록현황 xlsx 다운로드 정보를 찾는다."""
    response = session.get(LIST_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a"):
        info = get_file_information(anchor.get("onclick", ""))
        if not info:
            continue
        file_name = info["saved_file_name"]
        if not file_name.lower().endswith(".xlsx") or "자동차 등록자료" not in file_name:
            continue
        if file_name not in seen:
            found.append(info)
            seen.add(file_name)
    if not found:
        raise RuntimeError("자동차 등록자료 엑셀 링크를 찾지 못했습니다. 통계누리 페이지 구조를 확인하세요.")
    return found


def download_one_xlsx(file_info: dict[str, str], session: requests.Session) -> Path | None:
    """엑셀 한 개를 내려받고, 이미 있으면 건너뛴다."""
    DATA_DIR.mkdir(exist_ok=True)
    output_path = DATA_DIR / file_info["saved_file_name"]
    if output_path.exists():
        print(f"이미 존재하여 건너뜀: {output_path.name}")
        return None

    params = {
        "oFileName": file_info["original_file_name"],
        "rFileName": file_info["saved_file_name"],
        "midpath": file_info["midpath"],
    }
    print(f"다운로드: {output_path.name}")
    response = session.get(DOWNLOAD_URL, params=params, timeout=60)
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise RuntimeError(f"엑셀 파일이 아닌 응답을 받았습니다: {output_path.name}")

    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_bytes(response.content)
    temporary_path.replace(output_path)
    return output_path


def main() -> None:
    headers = {"User-Agent": "Mozilla/5.0 (educational vehicle-registration dashboard)"}
    with requests.Session() as session:
        session.headers.update(headers)
        files = find_vehicle_files(session)
        if DOWNLOAD_COUNT is not None:
            files = files[:DOWNLOAD_COUNT]

        print(f"확인할 파일 수: {len(files)}")
        downloaded = 0
        for index, info in enumerate(files, start=1):
            print(f"[{index}/{len(files)}]", end=" ")
            if download_one_xlsx(info, session) is not None:
                downloaded += 1
            time.sleep(REQUEST_DELAY_SECONDS)
    print(f"완료: 새로 받은 파일 {downloaded}개")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("수집 중 오류가 발생했습니다.")
        print(error)
