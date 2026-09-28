# 전국 자동차 등록 현황 및 기업 FAQ 조회 시스템

KOSIS 자동차 등록 통계와 현대자동차·기아자동차 FAQ를 조회하는 Streamlit 웹 애플리케이션입니다. 자동차 등록 통계는 KOSIS OpenAPI에서 가져오고, FAQ는 기업별 웹사이트에서 수집한 데이터를 활용합니다.

## 주요 기능

- **자동차 등록 현황**: 연도와 월을 선택하고 지역 및 차종별 등록 현황을 확인합니다.
- **요약 지표**: 전체 등록 대수와 승용·승합·화물·특수 차종별 대수를 표시합니다.
- **지역별 분석**: 지역별 등록 대수 막대 차트와 차종별 상세 표를 제공합니다.
- **FAQ 조회**: 현대 또는 기아를 선택하고 카테고리별 FAQ 목록과 상세 답변을 확인합니다.
- **FAQ 수집**: Selenium 기반 기업별 크롤러가 FAQ를 CSV로 저장하고 MySQL에 적재합니다.

## 기술 스택

- **언어**: Python 3.12
- **프레임워크**: Streamlit
- **데이터 처리**: Pandas
- **외부 통신**: Requests, KOSIS OpenAPI
- **데이터베이스**: MySQL
- **크롤링**: Selenium

## 프로젝트 구조

```text
.
├── app.py                    # Streamlit 앱 진입점과 사이드바 페이지 구성
├── pages/
│   ├── registration.py       # KOSIS 자동차 등록 현황
│   └── faq.py                # 현대·기아 FAQ 조회
├── components/
│   ├── charts.py             # 등록 통계 차트 컴포넌트
│   └── faq_card.py           # FAQ 카드 컴포넌트
└── crawler/
    ├── hyundai.py            # 현대 FAQ 크롤링 및 저장
    ├── kia.py                # 기아 FAQ 크롤링 및 저장
    └── csv/                  # 크롤러 결과 CSV
```

## 환경 설정

KOSIS OpenAPI 키를 발급받아 `.streamlit/secrets.toml`에 설정합니다.

```toml
KOSIS_API_KEY = "your_KOSIS_API_key"
```

MySQL 접속 정보 설정
```python
# faq.py, hyundai.py, kia.py 파일 안에 있는 db_config에 자신의 데이터베이스 비밀번호를 입력
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "your_database_password",
    "database": "your_database_name",
    "port": 3306,
    "charset": "utf8mb4"
}
```

## 실행 방법

```bash
# 파이썬 패키지 설치
pip install streamlit pandas requests pymysql selenium

# 수집기 실행 - 앱 실행하기 전에 반드시 수집기를 실행하여 데이터를 생성
python crawler/hyundai.py
python crawler/kia.py

# 앱 실행
streamlit run app.py
```

## FAQ 데이터베이스

FAQ 페이지는 아래 데이터베이스와 테이블을 조회합니다.

| 브랜드 | 데이터베이스 | 테이블 |
| --- | --- | --- |
| 현대 | `hyundai_db` | `hyundai_faq` |
| 기아 | `kia_db` | `kia_faq` |

## 단기 계획
- [ ] 자동차 등록 현황 화면에서 KOSIS OpenAPI 비즈니스 로직 분리
- [ ] 현대, 기아 FAQ 수집기 추상화
- [ ] 자동차 등록 현황 CSV 파일 다운로드 기능 구현
- [ ] README 정리