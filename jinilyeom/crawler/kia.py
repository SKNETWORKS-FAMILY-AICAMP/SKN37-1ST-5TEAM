# 기아자동차 FAQ 크롤러
import time
import pandas as pd
import os
import pymysql

from selenium import webdriver
from selenium.webdriver.common.by import By

URL = "https://www.kia.com/kr/customer-service/center/faq"

# 크롬 브라우저 실행
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options = options)

driver.get(URL)

time.sleep(3)

results = []

def save_kia_faq_to_db(csv_file_path):
    # CSV 파일 읽기
    try:
        df = pd.read_csv(csv_file_path, encoding="utf-8-sig")
    except FileNotFoundError:
        print(f"Error: '{csv_file_path}' 파일을 찾을 수 없습니다.")
        return

    # MySQL 데이터베이스 연결 정보
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "7276",
        "database": "kia_db",
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
        CREATE TABLE IF NOT EXISTS kia_faq (
            id INT AUTO_INCREMENT PRIMARY KEY,
            brand VARCHAR(50) DEFAULT '기아',
            category VARCHAR(100),
            page INT,
            question TEXT,
            answer TEXT
        ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
        """
        cursor.execute(create_table_sql)

        # 데이터 삽입 쿼리
        insert_sql = """
        INSERT INTO kia_faq (brand, category, page, question, answer)
        VALUES (%s, %s, %s, %s, %s)
        """

        # DataFrame 행들을 튜플 형태 리스트로 변환
        data_to_insert = []
        for _, row in df.iterrows():
            data_to_insert.append(
                (
                    "기아",
                    row["카테고리"],
                    int(row["페이지"]),
                    row["질문"],
                    row["답변"]
                )
            )

        # 한 번에 대량 저장
        cursor.executemany(insert_sql, data_to_insert)
        print(f" 성공적으로 {len(data_to_insert)}건의 데이터를 'kia_faq' 테이블에 저장했습니다.")
    except Exception as e:
        print(f"DB 저장 중 오류 발생: {e}")
    finally:
        # DB 연결 해제
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals():
            conn.close()

try:
    # 카테고리 탭 목록 가져오기
    category_tabs = driver.find_elements(By.CSS_SELECTOR, ".cmp-faq__tab-list button, .cmp-tabs__tab, .cmp-tabs__tab-button, ul[role='tablist'] button, ul[role='tablist'] li")
    
    if not category_tabs:
        category_tabs = driver.find_elements(By.XPATH, "//ul[contains(@class,'tab')]//button | //ul[contains(@class,'tab')]//a | //div[contains(@class,'tab')]//button")

    total_categories = len(category_tabs)
    print(f"총 {total_categories}개의 카테고리 탭")

    # "차량 구매"부터 "기타" 카테고리까지 순서대로 클릭
    for cat_idx in range(1, total_categories):
        # 페이지 이동/갱신 시 요소 끊김 방지를 위해 매번 탭 목록을 다시 가져옵니다.
        category_tabs = driver.find_elements(By.CSS_SELECTOR, ".cmp-faq__tab-list button, .cmp-tabs__tab, .cmp-tabs__tab-button, ul[role='tablist'] button, ul[role='tablist'] li")

        if not category_tabs:
            category_tabs = driver.find_elements(By.XPATH, "//ul[contains(@class,'tab')]//button | //ul[contains(@class,'tab')]//a | //div[contains(@class,'tab')]//button")

        if cat_idx >= len(category_tabs):
            break

        current_tab = category_tabs[cat_idx]
        cat_name = current_tab.text.strip().replace("\n", " ")
        
        # 탭 이름이 없거나 TOP 10 문구가 포함된 경우 제외
        if not cat_name or "TOP" in cat_name.upper():
            continue

        print()
        print("=" * 80)
        print(f"[{cat_idx}/{total_categories-1}] 카테고리 수집 시작: {cat_name}")
        print("=" * 80)

        # 카테고리 탭 클릭
        driver.execute_script("arguments[0].click();", current_tab)
        # 카테고리 전환 후 데이터 로딩 대기
        time.sleep(2.5)

        page_num = 1

        # 해당 카테고리의 모든 페이지 순회 (1페이지부터 끝까지)
        while True:
            print(f"---> [{cat_name}] {page_num}페이지 수집 중...")

            # 질문 버튼 찾기
            questions = driver.find_elements(By.CSS_SELECTOR, ".cmp-accordion__header button, .cmp-accordion__button, button.cmp-accordion__title, [data-cmp-hook-accordion='button']")

            if not questions:
                questions = driver.find_elements(By.XPATH, "//div[contains(@class,'accordion')]//button | //li[contains(@class,'accordion')]//button")

            print(f"발견된 질문 개수: {len(questions)}개")

            if len(questions) == 0:
                print("수집할 FAQ 항목이 없습니다.")
                break

            # 질문과 답변 수집
            for q_idx in range(len(questions)):
                try:
                    # 클릭 동작 후 DOM 변경에 대비해 질문 목록 재조회
                    q_list = driver.find_elements(By.CSS_SELECTOR, ".cmp-accordion__header button, .cmp-accordion__button, button.cmp-accordion__title, [data-cmp-hook-accordion='button']")

                    if not q_list:
                        q_list = driver.find_elements(By.XPATH, "//div[contains(@class,'accordion')]//button | //li[contains(@class,'accordion')]//button")

                    if q_idx >= len(q_list):
                        break

                    q_btn = q_list[q_idx]
                    question_text = q_btn.text.strip().replace("\n", " ")

                    # 질문 텍스트가 비어있거나 메뉴 버튼일 경우 제외
                    if not question_text or question_text in ["KR", "통합검색", "메뉴"]:
                        continue

                    # 질문 클릭하여 답변 보기
                    driver.execute_script("arguments[0].click();", q_btn)
                    time.sleep(0.5)

                    # 답변 텍스트 가져오기
                    try:
                        answer_elem = q_btn.find_element(By.XPATH, "./ancestor::*[contains(@class,'accordion__item') or contains(@class,'cmp-accordion')]//div[contains(@class,'content') or contains(@class,'panel')]")
                        answer_text = answer_elem.text.strip().replace("\n", " ")
                    except:
                        try:
                            answer_elem = q_btn.find_element(By.XPATH, "./following::div[1]")
                            answer_text = answer_elem.text.strip().replace("\n", " ")
                        except:
                            answer_text = "답변 내용을 불러오지 못했습니다."

                    # TODO: 브랜드 추가, 프린트 포맷 변경
                    results.append({
                        "브랜드": "기아",
                        "카테고리": cat_name,
                        "페이지": page_num,
                        "질문": question_text,
                        "답변": answer_text
                    })
                    print(f"  [수집 완료 - {page_num}p] 질문: {question_text[:25]}...")
                except Exception:
                    continue

            # 다음 페이지 클릭
            next_page_num = page_num + 1
            
            # 숫자 버튼 직접 클릭 (예: 6, 7, 8 ...)
            try:
                next_btn = driver.find_element(
                    By.XPATH, 
                    f"//button[normalize-space(text())='{next_page_num}'] | //a[normalize-space(text())='{next_page_num}']"
                )
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(2)
                page_num += 1
            except Exception:
                # 숫자 버튼이 안 보일 경우 다음 페이지 목록(>) 버튼 클릭
                try:
                    next_group_btn = driver.find_element(
                        By.XPATH,
                        "//button[contains(@class, 'next') or contains(@class, 'btn-next') or contains(@aria-label, '다음')] | //a[contains(@class, 'next') or contains(@class, 'btn-next') or contains(@aria-label, '다음')]"
                    )
                    driver.execute_script("arguments[0].click();", next_group_btn)
                    time.sleep(2)
                    page_num += 1
                except Exception:
                    print(f"[{cat_name}] 카테고리의 마지막 페이지입니다.")
                    break
finally:
    # CSV 파일로 저장
    if results:
        df = pd.DataFrame(results)

        output_dir = r"C:\Users\playdata2\Projects\first-unit-project\crawler\csv"
        csv_file_path = output_dir + r"\kia_faq.csv"

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        df.to_csv(csv_file_path, index = False, encoding = "utf-8-sig")

        print()
        print("=" * 80)
        print("수집 완료")
        print("=" * 80)
        print("총 수집 데이터:", len(results))
        print()

        save_kia_faq_to_db(csv_file_path)
    else:
        print()
        print("수집된 데이터가 없습니다.")

    driver.quit()

if __name__ == "__main__":
    output_dir = r"C:\Users\playdata2\Projects\first-unit-project\crawler\csv"
    csv_file_path = output_dir + r"\kia_faq.csv"

    save_kia_faq_to_db(csv_file_path)