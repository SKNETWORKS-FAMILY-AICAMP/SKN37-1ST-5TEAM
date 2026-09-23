import os
import time
import random
import pymysql
import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# 1. 환경 설정 및 DB 연결
# ==========================================
load_dotenv()
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'your_password')
DB_NAME = os.getenv('DB_NAME', 'korea_car')

def init_db():
    conn = pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME, charset='utf8mb4'
    )
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faq (
                id INT AUTO_INCREMENT PRIMARY KEY,
                company VARCHAR(50),
                category_main VARCHAR(100),
                category_sub VARCHAR(100),
                question TEXT,
                answer TEXT
            ) DEFAULT CHARSET=utf8mb4;
        """)
        cursor.execute("TRUNCATE TABLE faq;") # 기존 데이터 초기화
    conn.commit()
    return conn

# ==========================================
# 2. 브라우저 세팅 및 공통 유틸리티 (쉐보레 안티봇 로직 적용)
# ==========================================
def get_driver():
    options = Options()
    
    # 봇 탐지 우회
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=ko-KR")
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    # options.add_argument("--headless") # 화면 없이 실행하려면 주석 해제

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # CDP를 통한 런타임 위장
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko', 'en-US', 'en'] });
        """
    })
    return driver

def random_sleep(min_sec=1.2, max_sec=2.5):
    time.sleep(random.uniform(min_sec, max_sec))

def safe_click(driver, element):
    # 스크롤 중앙 이동 후 JavaScript를 통한 안전 클릭 (오버레이 방어)
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", element)
    time.sleep(0.3)
    try:
        element.click()
    except:
        driver.execute_script("arguments[0].click();", element)

# ==========================================
# 3. [기아] 수집 함수
# ==========================================
def fetch_kia_pages(driver, main_category, faq_data_list, collected_questions):
    page_num = 1
    while True:
        print(f"     ↳ [기아] {main_category} - {page_num}페이지 수집 중...")
        random_sleep(1.5, 2.5)
        
        faq_items = driver.find_elements(By.CSS_SELECTOR, "div.cmp-accordion__item")
        for i in range(len(faq_items)):
            try:
                curr_items = driver.find_elements(By.CSS_SELECTOR, "div.cmp-accordion__item")
                if i >= len(curr_items): break
                item = curr_items[i]
                
                title_elem = item.find_element(By.CSS_SELECTOR, ".cmp-accordion__title")
                question = driver.execute_script("return arguments[0].innerText;", title_elem).strip()
                
                btn = item.find_element(By.CSS_SELECTOR, "button.cmp-accordion__button")
                safe_click(driver, btn)
                time.sleep(0.8)
                
                panel = item.find_element(By.CSS_SELECTOR, ".cmp-accordion__panel")
                answer = driver.execute_script("return arguments[0].innerText || arguments[0].textContent;", panel).strip()
                
                if answer and question not in collected_questions:
                    collected_questions.add(question)
                    faq_data_list.append({
                        "company": "기아", "category_main": main_category, "category_sub": "일반",
                        "question": question, "answer": answer
                    })
            except Exception:
                continue
                
        try:
            active_page_elem = driver.find_element(By.CSS_SELECTOR, "ul.paging-list li.is-active a")
            next_page_str = str(int(active_page_elem.text.strip()) + 1)
            clicked = False
            links = driver.find_elements(By.CSS_SELECTOR, "ul.paging-list li a")
            for link in links:
                if link.text.strip() == next_page_str:
                    safe_click(driver, link)
                    page_num += 1
                    clicked = True
                    break
            if not clicked: break
        except Exception:
            break

# ==========================================
# 4. [현대] 수집 함수
# ==========================================
def fetch_hyundai_pages(driver, main_category, sub_category, faq_data_list, collected_questions):
    page_num = 1
    wait = WebDriverWait(driver, 10)
    
    while True:
        print(f"     ↳ [현대] {main_category} > {sub_category} - {page_num}페이지 수집 중...")
        random_sleep(2, 3) 
        
        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.list-item")))
            list_items = driver.find_elements(By.CSS_SELECTOR, "div.list-item")
        except Exception:
            break
            
        for i in range(len(list_items)):
            try:
                curr_items = driver.find_elements(By.CSS_SELECTOR, "div.list-item")
                if i >= len(curr_items): break
                item = curr_items[i]
                
                content_span = item.find_element(By.CSS_SELECTOR, "span.list-content")
                question = driver.execute_script("return arguments[0].innerText;", content_span).strip()
                if not question: continue
                
                title_btn = item.find_element(By.CSS_SELECTOR, "button.list-title")
                safe_click(driver, title_btn)
                time.sleep(1.0) 
                
                curr_items = driver.find_elements(By.CSS_SELECTOR, "div.list-item")
                conts_div = curr_items[i].find_element(By.CSS_SELECTOR, "div.conts")
                answer = driver.execute_script("return arguments[0].innerText || arguments[0].textContent;", conts_div).strip()
                
                if answer and question not in collected_questions:
                    collected_questions.add(question)
                    faq_data_list.append({
                        "company": "현대", "category_main": main_category, "category_sub": sub_category,
                        "question": question, "answer": answer
                    })
            except Exception:
                continue
                
        try:
            page_buttons = driver.find_elements(By.CSS_SELECTOR, "ul.el-pager li.number")
            clicked_next = False
            for btn in page_buttons:
                if btn.text.strip() == str(page_num + 1):
                    safe_click(driver, btn)
                    clicked_next = True
                    break
            
            if clicked_next:
                page_num += 1
            else:
                next_arrow = driver.find_element(By.CSS_SELECTOR, "button.btn-next")
                if "ative" in next_arrow.get_attribute("class"): 
                    safe_click(driver, next_arrow)
                    page_num += 1
                else:
                    break 
        except Exception:
            break

# ==========================================
# 5. [쉐보레] 수집 보조 및 메인 함수
# ==========================================
def extract_chevrolet_answer(driver, q_btn):
    btn_class = q_btn.get_attribute("class") or ""
    is_expanded = q_btn.get_attribute("aria-expanded")
    
    if "active" not in btn_class and is_expanded != "true":
        safe_click(driver, q_btn)
        time.sleep(0.5)

    answer_xpaths = [
        "./following::div[contains(@class, 'q-text')][1]",
        "./following::div[contains(@class, 'col-con')][1]",
        "./ancestor::*[contains(@class, 'expander')]//*[contains(@class, 'q-text')]",
        "./following-sibling::*[contains(@class, 'content') or contains(@class, 'col-con')]"
    ]

    for xpath in answer_xpaths:
        try:
            answer_el = q_btn.find_element(By.XPATH, xpath)
            text = driver.execute_script("return arguments[0].innerText || arguments[0].textContent;", answer_el).strip()
            if text: return text
        except NoSuchElementException:
            continue
    return ""

def fetch_chevrolet_pages(driver, faq_data_list, collected_questions):
    wait = WebDriverWait(driver, 10)
    print("\n▶ 쉐보레 FAQ 크롤링 시작...")
    driver.get("https://www.chevrolet.co.kr/faq")
    random_sleep(3.5, 4.5)

    category_xpath = "//a[@data-dtm='tertiary nav'] | //a[.//span[contains(@class, 'move-text')]]"
    try:
        wait.until(EC.presence_of_all_elements_located((By.XPATH, category_xpath)))
        categories = driver.find_elements(By.XPATH, category_xpath)
        category_count = len(categories)

        for cat_idx in range(category_count):
            categories = driver.find_elements(By.XPATH, category_xpath)
            current_cat = categories[cat_idx]

            try:
                move_text_el = current_cat.find_element(By.XPATH, ".//span[contains(@class, 'move-text')]")
                cat_name = move_text_el.text.strip()
            except NoSuchElementException:
                cat_name = current_cat.get_attribute("title") or current_cat.text.strip()
            if not cat_name: cat_name = f"카테고리_{cat_idx + 1}"

            print(f"\n - [쉐보레] 대분류: {cat_name} 탭 진입...")
            safe_click(driver, current_cat)
            random_sleep(2.5, 3.5)

            # 더보기 펼치기
            while True:
                more_btns = driver.find_elements(By.XPATH, "//button[contains(@class, 'more') or contains(text(), '더보기')] | //a[contains(@class, 'more') or contains(text(), '더보기')]")
                if more_btns and more_btns[0].is_displayed():
                    try:
                        safe_click(driver, more_btns[0])
                        random_sleep(1.2, 1.8)
                    except Exception:
                        break
                else:
                    break

            # 질문 추출
            question_xpath = "//div[contains(@class, 'gb-expander-btn')]"
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, question_xpath)))
            except TimeoutException:
                print(f"   ! [{cat_name}] 질문이 없습니다.")
                continue

            q_buttons = driver.find_elements(By.XPATH, question_xpath)
            for idx in range(len(q_buttons)):
                try:
                    current_q_buttons = driver.find_elements(By.XPATH, question_xpath)
                    if idx >= len(current_q_buttons): break
                    target_btn = current_q_buttons[idx]

                    try:
                        h6_el = target_btn.find_element(By.XPATH, ".//h6[contains(@class, 'gb-expander-headline')]")
                        q_text = h6_el.text.strip().replace("\n", " ")
                    except NoSuchElementException:
                        q_text = target_btn.text.strip().replace("\n", " ")

                    a_text = extract_chevrolet_answer(driver, target_btn)

                    if a_text and q_text not in collected_questions:
                        collected_questions.add(q_text)
                        faq_data_list.append({
                            "company": "쉐보레",
                            "category_main": cat_name,
                            "category_sub": "일반", # 쉐보레는 중분류가 없으므로 일반으로 통일
                            "question": q_text,
                            "answer": a_text
                        })
                except Exception:
                    continue
    except Exception as e:
        print(f"쉐보레 크롤링 중 오류: {e}")

# ==========================================
# 6. 메인 통합 크롤러 실행
# ==========================================
def crawl_all_faqs():
    driver = get_driver()
    faq_data_list = []
    collected_questions = set()
    
    try:
        wait = WebDriverWait(driver, 10)
        
        # --- 1. 기아 ---
        print("\n▶ 기아 FAQ 크롤링 접속...")
        driver.get("https://www.kia.com/kr/customer-service/center/faq")
        random_sleep(3, 5)
        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#tab-list > li > button")))
            tabs_count = len(driver.find_elements(By.CSS_SELECTOR, "#tab-list > li > button"))
            for i in range(1, tabs_count):
                tabs = driver.find_elements(By.CSS_SELECTOR, "#tab-list > li > button")
                main_category = tabs[i].text.strip()
                print(f"\n[기아 대분류] {main_category} 진입...")
                safe_click(driver, tabs[i])
                fetch_kia_pages(driver, main_category, faq_data_list, collected_questions)
        except Exception as e:
            print(f"기아 크롤링 중 오류: {e}")

        # --- 2. 현대 ---
        print("\n▶ 현대자동차 FAQ 크롤링 접속...")
        driver.get("https://www.hyundai.com/kr/ko/e/customer/center/faq")
        random_sleep(4, 6)
        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".tab-menu__icon button")))
            main_tabs_count = len(driver.find_elements(By.CSS_SELECTOR, ".tab-menu__icon button"))
            for i in range(main_tabs_count):
                main_tabs = driver.find_elements(By.CSS_SELECTOR, ".tab-menu__icon button")
                if i >= len(main_tabs): break
                main_category = main_tabs[i].text.strip()
                if not main_category or main_category == "전체": continue
                    
                print(f"\n[현대 대분류] {main_category} 진입...")
                safe_click(driver, main_tabs[i])
                random_sleep(2, 3) 
                
                sub_tabs = driver.find_elements(By.CSS_SELECTOR, ".tab-menu-sub button, .sub-tab button")
                if len(sub_tabs) > 0:
                    sub_tabs_count = len(sub_tabs)
                    for j in range(sub_tabs_count):
                        curr_sub_tabs = driver.find_elements(By.CSS_SELECTOR, ".tab-menu-sub button, .sub-tab button")
                        if j >= len(curr_sub_tabs): break
                        sub_category = curr_sub_tabs[j].text.strip()
                        if sub_category == "전체": continue 
                            
                        print(f"   [현대 중분류] {sub_category} 선택...")
                        safe_click(driver, curr_sub_tabs[j])
                        random_sleep(2, 3) 
                        fetch_hyundai_pages(driver, main_category, sub_category, faq_data_list, collected_questions)
                else:
                    fetch_hyundai_pages(driver, main_category, "일반", faq_data_list, collected_questions)
        except Exception as e:
            print(f"현대 크롤링 중 오류: {e}")

        # --- 3. 쉐보레 ---
        fetch_chevrolet_pages(driver, faq_data_list, collected_questions)
            
    finally:
        driver.quit()

    # ================== CSV 저장 및 DB 적재 ==================
    csv_filename = "faq_data_total.csv" # 3사 통합본 파일명 변경
    print(f"\n▶ 수집된 데이터를 '{csv_filename}' 파일로 추출합니다...")
    df_faq = pd.DataFrame(faq_data_list)
    df_faq.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"✅ CSV 파일 저장 완료 (총 {len(df_faq)}건 수집)")

    print("\n▶ 데이터베이스에 3사 통합 FAQ 적재를 시작합니다...")
    conn = init_db()
    try:
        df_load = pd.read_csv(csv_filename)
        with conn.cursor() as cursor:
            insert_query = """
                INSERT INTO faq (company, category_main, category_sub, question, answer) 
                VALUES (%s, %s, %s, %s, %s)
            """
            data_tuples = [
                (row['company'], row['category_main'], row['category_sub'], row['question'], row['answer'])
                for _, row in df_load.iterrows()
            ]
            cursor.executemany(insert_query, data_tuples)
            
        conn.commit()
        print("✅ 데이터베이스(korea_car.faq) 저장 성공! (현대/기아/쉐보레 통합 완료)")
        
    finally:
        conn.close()

if __name__ == "__main__":
    crawl_all_faqs()