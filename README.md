# 자동차 등록현황 및 FAQ 인사이트 플랫폼

### 전국 자동차 등록 통계와 제조사 FAQ를 한 화면에서 조회하는 데이터 대시보드

## 팀 소개

팀원 : 김재홍, 김지훈, 정영석, 김정민

## 개발 기간

2026.03.25 - 2026.03.31(총 7일)

---

## 프로젝트 개요

### 1. 주제

국토교통 통계누리의 월별 자동차 등록현황을 정리하여 지역·용도·연료·성별/연령별 등록대수를 탐색하고, 현대·기아·쉐보레 FAQ를 함께 검색하는 대시보드입니다.

### 2. 선정 배경

- 자동차 등록 통계는 월별 엑셀 문서와 여러 통계표로 나뉘어 있어 비교하기 어렵습니다.
- 동일한 값이라도 시군구 명칭, 연령대 띄어쓰기, 표의 머리글 구조가 시기마다 달라 그대로 합치면 오류가 생길 수 있습니다.
- 등록현황을 확인하는 사용자에게 제조사 FAQ까지 같은 화면에서 제공하면 정보 탐색 흐름을 단순화할 수 있습니다.

### 3. 프로젝트 목표

1. 월별 자동차 등록 원자료를 하나의 정규화된 데이터 구조로 관리합니다.
2. 지역별·용도별·연료별·성별/연령별 등록현황을 필터와 차트로 비교합니다.
3. MySQL을 우선 조회하고, 연결이 어려울 때는 CSV로 자동 대체하여 화면을 유지합니다.
4. 제조사·대분류·소분류·검색어로 FAQ를 탐색합니다.

### 4. 구현 결과

- 자동차 등록 데이터: **261,751행**, **2016-01 ~ 2026-08** 기준으로 MySQL 적재 확인
- FAQ 데이터: 현대·기아·쉐보레 **589건** 적재 확인
- Streamlit 대시보드와 정적 HTML 목업 모두 제공

---

## 기술 스택

- Language: Python 3.12+ 권장
- Database: MySQL 8.x
- Web Framework: Streamlit
- Data: Pandas, CSV
- Visualization: Plotly
- Static prototype: HTML, CSS, JavaScript

## 사용한 데이터

- [국토교통 통계누리 자동차등록현황보고](https://stat.molit.go.kr/portal/cate/statView.do?hRsId=58)
- 프로젝트에서 정리한 `자동차_등록현황_통합_검증.csv`
- 프로젝트에서 정리한 `faq_data_total.csv`

> 자동차 등록 통계는 등록대수 통계이며 차량 판매량이나 구매 의향을 직접 뜻하지 않습니다.

## 파일 구조

```text
project1/
├── .env                                  # MySQL 접속값(공개 금지)
├── .gitignore                            # 비밀값·캐시 제외 규칙
├── requirements.txt                      # Python 패키지 목록
├── README.md                             # 프로젝트 안내
├── DATABASE_DESIGN.md                    # ERD 및 테이블 설계
├── dashboard_mockup.html                 # CSV 기반 정적 HTML 대시보드
├── streamlit_mysql.py                    # MySQL 우선 Streamlit 대시보드
├── car_dashboard.py                       # 통계누리 월별 엑셀 수집
├── csv_from_excel.py                      # 엑셀 → 통합·검증 CSV 변환
├── load_mysql.py                         # CSV → MySQL 복원/적재 도구
├── update_csv_and_mysql.py               # 변환·MySQL 적재 통합 실행
├── south-korea-map.png                   # 지역별 화면 지도 이미지
└── data/
    ├── 자동차_등록현황_통합_검증.csv     # 자동차 등록현황 화면·DB 적재 원본
    └── faq_data_total.csv                # FAQ 화면·DB 적재 원본
```

## 데이터베이스 구조

상세 ERD와 컬럼 정의는 [DATABASE_DESIGN.md](DATABASE_DESIGN.md)를 확인하세요.

- `vehicle_registration_fact`: 자동차 등록현황 분석용 사실 테이블
- `faq`: 제조사 FAQ 검색 테이블

두 테이블은 서로 독립된 분석 데이터입니다. FAQ의 제조사명은 자동차 등록 통계의 분류 기준과 직접 연결되는 외래 키가 아니므로, DB 외래 키 관계를 만들지 않았습니다.

## 실행 방법

### 1. Conda 환경 준비

```bash
conda activate car-dashboard
cd C:\Users\s2sad\project1
pip install -r requirements.txt
```

### 2. `.env` 확인

프로젝트 최상위의 `.env`에 다음 항목을 둡니다. 기존 `.env`를 삭제할 필요 없이, 같은 파일에 항목을 유지·수정하면 됩니다.

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=본인의_비밀번호
MYSQL_DATABASE=vehicle_db
```

`MYSQL_PORT`는 반드시 숫자만 입력합니다. 예: `3306`.

### 3. MySQL 데이터 복원 또는 갱신

MySQL에 테이블과 데이터가 이미 있으면 이 단계는 생략할 수 있습니다. CSV 기준으로 다시 맞추려면 다음을 실행합니다.

```bash
python load_mysql.py --replace --replace-faq
```

테이블 구조가 이전 버전이라 오류가 날 때만 다음을 사용합니다. 이 명령은 기존 두 테이블을 다시 만들 수 있으므로 주의합니다.

```bash
python load_mysql.py --reset --replace --replace-faq
```

### 4. Streamlit 실행

```bash
streamlit run streamlit_mysql.py
```

기본 주소는 보통 `http://localhost:8501`입니다. 이 앱은 MySQL 조회를 우선 시도하고, 실패하면 `data` 폴더의 CSV를 읽습니다.

### 5. 정적 HTML 실행

브라우저에서 CSV를 읽으려면 `file:///`로 직접 열지 말고 간단한 로컬 서버를 실행합니다.

```bash
python -m http.server 8765
```

이후 [http://127.0.0.1:8765/dashboard_mockup.html](http://127.0.0.1:8765/dashboard_mockup.html)로 접속합니다. 중지는 실행한 창에서 `Ctrl + C`입니다.

## 주요 기능

- 통합·지역별·용도별·연료별·성별/연령별 탭 조회
- 연도·월 다중 선택과 시도 선택에 따른 비교 차트 및 데이터 표
- 지역별 지도 점 선택과 시군구 조회
- 필터 결과 CSV 다운로드
- FAQ 제조사·대분류·소분류·키워드 검색
- MySQL 장애 시 CSV 자동 대체

## 데이터 처리에서 반영한 점

- 시군구, 연령대 등 표기 차이를 정리해 동일 항목이 중복 분리되는 문제를 줄였습니다.
- `10대이하`/`10대 이하`, `90대이상`/`90대 이상`처럼 띄어쓰기가 다른 값은 화면에서 통일해 표시합니다.
- 등록대수는 각 통계표의 **계** 행을 기준으로 구성해 중복 합산을 피합니다.
- `record_key`와 고유 인덱스를 사용해 같은 기준년월·분류 조합이 중복 적재되지 않게 했습니다.

## 프로젝트 시연

1. Streamlit에서 자동차 등록현황 또는 FAQ를 선택합니다.
2. 자동차 등록현황은 상단 필터와 탭을 조합해 분석합니다.
3. FAQ는 제조사와 분류를 선택하거나 검색어를 입력해 질문과 답변을 확인합니다.
4. 필요한 결과는 표 아래의 다운로드 버튼으로 CSV로 받을 수 있습니다.

## 데이터 갱신 흐름

1. `python car_dashboard.py`로 통계누리의 새 월별 엑셀을 `data` 폴더에 추가합니다. 같은 이름의 기존 파일은 건너뜁니다.
2. `python csv_from_excel.py`로 원본 엑셀을 대시보드용 통합 CSV와 검증 CSV로 변환합니다.
3. `python load_mysql.py --replace --replace-faq`로 CSV 내용을 MySQL에 반영합니다.
4. 위 2~3단계를 한 번에 실행하려면 `python update_csv_and_mysql.py`를 사용합니다.

월별 원본 엑셀은 다시 수집해야 하지만, 수집·변환·적재 코드는 프로젝트에 유지합니다. 이전 화면 시안과 시험용 산출물만 정리 대상입니다.

## 기대 효과

- 월별 자동차 등록 흐름을 지역과 분류별로 빠르게 비교할 수 있습니다.
- 데이터 기반 발표·시연에서 동일한 데이터를 HTML과 Streamlit으로 보여줄 수 있습니다.
- FAQ 검색을 함께 제공하여 통계 조회와 고객 질문 탐색을 한 흐름으로 연결합니다.

## 회고

원자료의 표 구조와 명칭은 기간별로 달랐고, 단순히 엑셀을 합치면 원본과 다른 값이 나올 수 있었습니다. 원본 헤더·계 행·명칭을 다시 확인하고, MySQL 적재와 CSV 대체 방식을 함께 설계하면서 데이터 검증과 화면 구현이 분리될 수 없다는 점을 확인했습니다. 이후 화면 세부 기능과 지표 해석은 팀 논의를 통해 발전시킵니다.
