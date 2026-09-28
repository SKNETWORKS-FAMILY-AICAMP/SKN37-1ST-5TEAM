# 현대자동차 FAQ 크롤러
import time
import pandas as pd
import os
import pymysql

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path

URL = "https://www.hyundai.com/kr/ko/e/customer/center/faq"

categories = [
    "차량구매",
    "차량정비",
    "홈페이지",
    "블루멤버스",
    "블루링크",
    "Pleos 계정",
    "시승",
    "빌트인캠",
    "현대 디지털 키",
    "기타"
]

# =====================================================
# 크롬 실행
# =====================================================
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

# =====================================================
# 결과 저장
# =====================================================
result = []

# =====================================================
# 카테고리 클릭
# =====================================================
def click_category(category_name):
    print()
    print("=" * 70)
    print("카테고리 :", category_name)
    print("=" * 70)

    # role=tab 먼저 찾기
    elements = driver.find_elements(By.XPATH, "//*[@role='tab']")

    for element in elements:
        if not element.is_displayed():
            continue

        if element.text.strip() == category_name:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)

            time.sleep(0.5)

            element.click()

            time.sleep(2)

            print("카테고리 클릭 완료")

            return True

    # role=tab이 없을 경우 button 검색
    elements = driver.find_elements(By.XPATH, "//button")

    for element in elements:
        if not element.is_displayed():
            continue

        if element.text.strip() == category_name:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)

            time.sleep(0.5)

            element.click()

            time.sleep(2)

            print("카테고리 클릭 완료")

            return True

    print("카테고리를 찾지 못했습니다.")

    return False

# =====================================================
# 현재 페이지 FAQ 질문 가져오기
# =====================================================
def get_questions():
    elements = driver.find_elements(
        By.XPATH,
        """
        //button[
            starts-with(normalize-space(), '[')
        ]
        |
        //a[
            starts-with(normalize-space(), '[')
        ]
        """
    )

    questions = []

    for element in elements:
        if not element.is_displayed():
            continue

        text = element.text.strip()

        if text.startswith("["):
            questions.append(text)

    return questions

# =====================================================
# 질문 클릭
# =====================================================
def click_question(question):
    elements = driver.find_elements(
        By.XPATH,
        """
        //button[
            starts-with(normalize-space(), '[')
        ]
        |
        //a[
            starts-with(normalize-space(), '[')
        ]
        """
    )

    for element in elements:
        if not element.is_displayed():
            continue

        if element.text.strip() == question:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)

            time.sleep(0.3)

            element.click()

            time.sleep(0.5)

            return element

    return None

# =====================================================
# 답변 가져오기
# =====================================================
def get_answer(question_element, question):
    # 부모를 조금씩 올라가면서 답변 찾기
    for _ in range(7):
        try:
            parent = question_element.find_element(By.XPATH, "..")

            text = parent.text.strip()

            if len(text) > len(question):
                # 여러 FAQ를 한 번에 잡은 경우 제외
                if text.count("[") <= 1:
                    answer = text.replace(question, "", 1).strip()

                    if answer:
                        return answer

            question_element = parent
        except Exception:
            break

    return ""

# =====================================================
# 현재 페이지 FAQ 수집
# =====================================================
def collect_current_page(category_name, page_number):
    print()
    print(f"========== {category_name} / {page_number} 페이지 ==========")

    questions = get_questions()

    print("질문 수:", len(questions))

    for question in questions:
        try:
            question_element = click_question(question)

            if question_element is None:
                continue

            answer = get_answer(question_element, question)

            result.append({
                "브랜드": "현대",
                "카테고리": category_name,
                "페이지": page_number,
                "질문": question,
                "답변": answer
            })

            print("수집:", question[:50])
        except Exception as e:
            print("FAQ 수집 실패:", e)

# =====================================================
# 페이지 번호 가져오기
# =====================================================
def get_page_buttons():
    """
    현재 화면에 보이는 페이지 번호 버튼을 찾습니다.
    1, 2, 3 같은 숫자만 가져옵니다.
    """

    elements = driver.find_elements(By.XPATH, "//button | //a")

    page_buttons = []

    for element in elements:
        if not element.is_displayed():
            continue

        text = element.text.strip()

        if not text.isdigit():
            continue

        number = int(text)

        # 1 ~ 999 사이만 페이지 번호로 간주
        if 1 <= number <= 999:
            page_buttons.append((number, element))

    return page_buttons

# =====================================================
# 현재 페이지 번호
# =====================================================
def get_current_page():
    # aria-current 우선
    elements = driver.find_elements(By.XPATH, "//*[@aria-current='page']")

    for element in elements:
        if not element.is_displayed():
            continue

        text = element.text.strip()

        if text.isdigit():
            return int(text)

    # active / selected / on 클래스 확인
    elements = driver.find_elements(By.XPATH, "//button | //a")

    for element in elements:
        if not element.is_displayed():
            continue

        text = element.text.strip()

        if not text.isdigit():
            continue

        class_name = (element.get_attribute("class") or "").lower()

        if (
            "active" in class_name
            or "selected" in class_name
            or class_name.endswith("on")
            or " on " in class_name
        ):
            return int(text)

    return None

# =====================================================
# 페이지 이동
# =====================================================
def move_to_next_page(current_page):
    """
    1) 현재 화면에서 current_page보다 큰 페이지 번호를 찾습니다.
       예: 1, 2, 3 -> 2 클릭

    2) 더 이상 숫자가 없으면 '다음 페이지 그룹' 버튼을 찾습니다.
       예: 1, 2, 3 -> 4, 5, 6

    3) 실제 FAQ 내용이 변경되는지도 검사합니다.
    """

    # -------------------------------------------------
    # 현재 FAQ를 기억
    # -------------------------------------------------
    before_questions = get_questions()

    # -------------------------------------------------
    # 현재 화면의 숫자 페이지 버튼 확인
    # -------------------------------------------------
    page_buttons = get_page_buttons()
    page_buttons.sort(key = lambda x: x[0])

    for number, button in page_buttons:
        if number <= current_page:
            continue

        print(f"페이지 이동 : {current_page} -> {number}")

        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)

            time.sleep(0.3)

            # Stale element 방지
            button.click()

            # FAQ 목록이 변경될 때까지 기다림
            wait.until(lambda d: get_questions() != before_questions)

            time.sleep(1)

            return number
        except Exception as e:
            print("숫자 페이지 이동 실패:", e)

    # -------------------------------------------------
    # 현재 숫자 페이지가 마지막이라면
    # 다음 페이지 그룹 버튼 찾기
    # -------------------------------------------------
    print("현재 페이지 그룹의 마지막입니다.")

    # HTML의 텍스트만 보는 게 아니라
    # aria-label, title, data 속성까지 확인합니다.
    elements = driver.find_elements(By.XPATH, "//button | //a")

    candidates = []

    for element in elements:
        if not element.is_displayed():
            continue

        text = (element.text.strip())
        aria = (element.get_attribute("aria-label") or "").lower()
        title = (element.get_attribute("title") or "").lower()
        cls = (element.get_attribute("class") or "").lower()

        # 다음 페이지 관련 단어
        is_next = (
            "다음" in aria
            or "next" in aria
            or "다음" in title
            or "next" in title
            or "next" in cls
        )

        if not is_next:
            continue

        # Disabled 체크
        if element.get_attribute("disabled") is not None:
            continue

        if (element.get_attribute("aria-disabled") == "true"):
            continue

        candidates.append(element)

    # -------------------------------------------------
    # 다음 버튼 클릭
    # -------------------------------------------------
    for element in candidates:
        try:
            print("다음 페이지 그룹 버튼 발견")

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)

            time.sleep(0.3)

            element.click()

            # 내용이 바뀌는지 확인
            wait.until(lambda d: get_questions() != before_questions)

            time.sleep(1)

            new_page = get_current_page()

            if new_page is not None:
                return new_page

            return current_page + 1
        except Exception as e:
            print("다음 그룹 이동 실패:", e)

    # -------------------------------------------------
    # 여기까지 왔으면 마지막 페이지
    # -------------------------------------------------
    return None

# =====================================================
# 카테고리 전체 수집
# =====================================================
def collect_category(category_name):
    # -------------------------------------------------
    # 카테고리 선택
    # -------------------------------------------------
    if not click_category(category_name):
        print("카테고리 선택 실패:", category_name)
        return

    # -------------------------------------------------
    # 페이지 방문 기록
    # -------------------------------------------------
    visited_pages = set()

    page_number = 1

    while True:
        # 현재 실제 페이지 번호 확인
        current = get_current_page()

        if current is not None:
            page_number = current

        print()
        print(f"[{category_name}] 현재 페이지 = {page_number}")

        # -------------------------------------------------
        # 이미 방문한 페이지면 종료
        # -------------------------------------------------
        if page_number in visited_pages:
            print("이미 방문한 페이지입니다.")
            break

        # -------------------------------------------------
        # FAQ 수집
        # -------------------------------------------------
        collect_current_page(category_name, page_number)

        visited_pages.add(page_number)

        # -------------------------------------------------
        # 다음 페이지로 이동
        # -------------------------------------------------
        next_page = move_to_next_page(page_number)

        if next_page is None:
            print(f"[{category_name}] 마지막 페이지입니다.")
            break

        page_number = next_page

# =====================================================
# 메인
# =====================================================
try:
    for category in categories:
        print()
        print()
        print("#" * 80)

        print(f"### {category} 시작 ###")

        print("#" * 80)

        # -------------------------------------------------
        # 매 카테고리마다 FAQ 페이지를 처음부터 다시 열기
        # -------------------------------------------------
        driver.get(URL)

        time.sleep(3)

        # -------------------------------------------------
        # 해당 카테고리 전체 페이지 수집
        # -------------------------------------------------
        collect_category(category)
finally:
    driver.quit()

# =====================================================
# CSV 저장
# =====================================================
df = pd.DataFrame(result)

output_dir = r"C:\Users\playdata2\Projects\first-unit-project\crawler\csv"
csv_file_path = output_dir + r"\hyundai_faq.csv"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

df.to_csv(csv_file_path, index = False, encoding = "utf-8-sig")

print()
print("=" * 80)
print("수집 완료")
print("=" * 80)
print("총 수집 데이터:", len(df))
print()

def save_kia_faq_to_db(csv_file_path):
    # CSV 파일 읽기
    try:
        df = pd.read_csv(csv_file_path, encoding = "utf-8-sig")
    except FileNotFoundError:
        print(f"Error: '{csv_file_path}' 파일을 찾을 수 없습니다.")
        return

    if "페이지" in df.columns:
        df["페이지"] = df["페이지"].fillna(1).astype(int)

    df = df.fillna("")

    # MySQL 데이터베이스 연결 정보
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "7276",
        "database": "hyundai_db",
        "port": 3306,
        "charset": "utf8mb4",
        "autocommit": True
    }

    # PyMySQL을 통한 DB 연결
    try:
        conn = pymysql.connect(
            host = db_config.get("host"),
            user = db_config.get("user"),
            password = db_config.get("password"),
            port = db_config.get("port"),
            charset = db_config.get("charset"),
            autocommit = db_config.get("autocommit")
        )
        cursor = conn.cursor()

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_config.get("database")}` DEFAULT CHARACTER SET utf8mb4;")
        cursor.execute(f"USE `{db_config.get("database")}`;")

        # 테이블 생성
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS hyundai_faq (
            id INT AUTO_INCREMENT PRIMARY KEY,
            brand VARCHAR(50) DEFAULT '현대',
            category VARCHAR(100),
            page INT,
            question TEXT,
            answer TEXT
        ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
        """
        cursor.execute(create_table_sql)

        # 데이터 삽입 쿼리
        insert_sql = """
        INSERT INTO hyundai_faq (brand, category, page, question, answer)
        VALUES (%s, %s, %s, %s, %s)
        """

        # DataFrame 행들을 튜플 형태 리스트로 변환
        data_to_insert = []
        for _, row in df.iterrows():
            data_to_insert.append(
                (
                    "현대",
                    str(row["카테고리"]),
                    int(row["페이지"]),
                    str(row["질문"]),
                    str(row["답변"])
                )
            )

        # 한 번에 대량 저장
        cursor.executemany(insert_sql, data_to_insert)
        print(f" 성공적으로 {len(data_to_insert)}건의 데이터를 'hyundai_faq' 테이블에 저장했습니다.")
    except Exception as e:
        print(f"DB 저장 중 오류 발생: {e}")
    finally:
        # DB 연결 해제
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals():
            conn.close()

save_kia_faq_to_db(csv_file_path)