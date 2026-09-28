"""새 엑셀을 통합 CSV로 변환하고 MySQL에 반영한다.

작업 스케줄러에서 이 파일을 실행하면 된다. 수집은 별도 작업으로
car_dashboard.py를 먼저 실행하거나, 작업 스케줄러에 순서대로 등록한다.
"""

from pathlib import Path
import subprocess
import sys


PROJECT_DIR = Path(__file__).resolve().parent


def run(file_name: str, *arguments: str) -> None:
    command = [sys.executable, str(PROJECT_DIR / file_name), *arguments]
    subprocess.run(command, cwd=PROJECT_DIR, check=True)


def main() -> None:
    run("csv_from_excel.py")
    run("load_mysql.py", "--replace", "--replace-faq")
    print("CSV 변환과 MySQL 업데이트가 완료되었습니다.")


if __name__ == "__main__":
    main()
