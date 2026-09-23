"""
=============================================================================
[필독] 프로젝트 초기 세팅 스크립트
※ 주의: 크롤링(project1_crawling.py)을 실행하기 전에 반드시 이 파일(project1_db.py)부터 
먼저 실행하여 데이터베이스를 초기화하고 테이블을 생성해야 합니다!
=============================================================================
"""

import os
import pandas as pd
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.types import Integer, String
from dotenv import load_dotenv

# 1. DB 환경 변수 로드
load_dotenv()
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'your_password')
DB_NAME = os.getenv('DB_NAME', 'korea_car') 

print("======================================================")
print(" 🚀 프로젝트 초기 세팅 시작 (DB 초기화 및 데이터 적재) ")
print(" ※ 앱 실행(project1_streamlit.py) 전 반드시 이 과정이 선행되어야 합니다.")
print("======================================================\n")

# =====================================================================
# [작업 0] 데이터베이스(DB) 완전 초기화 (DROP & CREATE)
# =====================================================================
print(f"▶ [0/3] '{DB_NAME}' 데이터베이스 초기화(Reset) 진행 중...")
try:
    # DB 이름을 지정하지 않고 MySQL 서버에만 접속
    temp_conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
    with temp_conn.cursor() as cursor:
        # 1) 만약 기존에 똑같은 이름의 DB가 있다면 깨끗하게 삭제 (초기화)
        cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME};")
        # 2) 한글 깨짐 방지를 위한 설정(utf8mb4)과 함께 새 DB 생성
        cursor.execute(f"CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    temp_conn.commit()
    temp_conn.close()
    print(f"   -> 기존 DB 삭제 및 '{DB_NAME}' 새 데이터베이스 준비 완료!\n")
except Exception as e:
    print(f"   -> DB 초기화 중 오류 발생: {e}")

# SQLAlchemy 엔진 연결 (이제 무조건 깨끗한 DB가 존재하므로 안전하게 연결됨)
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}')
excel_file = '2026년_08월_자동차_등록자료_통계.xlsx'

# =====================================================================
# [작업 1] 지역 및 4단계 계층 상세 데이터 적재 (05.차종별_등록현황 시트)
# =====================================================================
print("▶ [1/3] 4단계 계층 및 지역별 상세 데이터 분석 중...")
df_detail = pd.read_excel(excel_file, sheet_name='05.차종별_등록현황(전체)', header=None)

date_str = str(df_detail.iloc[1, 0]).replace('조회년월:', '').strip()
year, month = date_str.split('.')
cities = df_detail.iloc[2, 5:22].str.strip().values

cats = df_detail.iloc[3:, 0:5].copy()
cats.columns = ['Total', 'L1', 'L2', 'L3', 'L4']
for col in cats.columns:
    if cats[col].dtype == 'object': cats[col] = cats[col].str.strip()

cats['L1_ffill'] = cats['L1'].ffill()
cats['L2_ffill'] = cats['L2'].ffill()
cats['L3_ffill'] = cats['L3'].ffill()

cats['Depth'] = 0
cats.loc[cats['L1'].notna(), 'Depth'] = 1
cats.loc[cats['L2'].notna(), 'Depth'] = 2
cats.loc[cats['L3'].notna(), 'Depth'] = 3
cats.loc[cats['L4'].notna(), 'Depth'] = 4

def clean_l1(x): return str(x).replace('차합계', '').replace('자동차 합계', '').replace('차 합계', '').strip() if pd.notna(x) else x
def clean_l2(x):
    if pd.isna(x): return x
    x = str(x).replace(' 계', '').replace(' 소계', '')
    for p in ['승용', '승합', '화물', '특수']:
        if x.startswith(p): x = x[len(p):]
    return x.strip()
def clean_l3(x): return str(x).replace(' 소계', '').split(' ')[-1].strip() if pd.notna(x) else x
def clean_l4(x):
    if pd.isna(x): return x
    parts = str(x).split()
    if len(parts) >= 2 and parts[-1] in ['이하', '미만', '이상']:
        return f"{parts[-2]} {parts[-1]}"
    return parts[-1]

cats['type_l1'] = cats['L1_ffill'].apply(clean_l1)
cats['type_l2'] = cats['L2_ffill'].apply(clean_l2)
cats['type_l3'] = cats['L3_ffill'].apply(clean_l3)
cats['type_l4'] = cats['L4'].apply(clean_l4)

values = df_detail.iloc[3:, 5:22]
values.columns = cities
full_df = pd.concat([cats[['Depth', 'type_l1', 'type_l2', 'type_l3', 'type_l4']], values], axis=1)

raw_data = full_df[full_df['Depth'] == 4].drop(columns=['Depth'])
tidy_detail = pd.melt(raw_data, id_vars=['type_l1', 'type_l2', 'type_l3', 'type_l4'], 
                      value_vars=cities[:-1], var_name='city', value_name='registered_count')

tidy_detail.insert(0, 'month', month)
tidy_detail.insert(0, 'year', year)
tidy_detail['registered_count'] = pd.to_numeric(tidy_detail['registered_count'], errors='coerce').fillna(0).astype(int)

# 중복 안전장치 (합산)
tidy_detail = tidy_detail.groupby(['city', 'year', 'month', 'type_l1', 'type_l2', 'type_l3', 'type_l4'], as_index=False)['registered_count'].sum()

dtype_mapping_detail = {
    'city': String(20), 'year': String(10), 'month': String(10),
    'type_l1': String(20), 'type_l2': String(20), 'type_l3': String(20), 'type_l4': String(30),
    'registered_count': Integer()
}
tidy_detail.to_sql(name='car_registration', con=engine, if_exists='replace', index=False, dtype=dtype_mapping_detail)

with engine.connect() as con:
    con.execute(text("ALTER TABLE car_registration ADD PRIMARY KEY (city, year, month, type_l1, type_l2, type_l3, type_l4);"))
    con.commit()
print("   -> 'car_registration' 테이블 적재 및 기본키(PK) 설정 완료!\n")


# =====================================================================
# [작업 2] 과거 연도별 히스토리 데이터 적재 (19.연도별 자동차 등록현황 시트)
# =====================================================================
print("▶ [2/3] 과거 연도별 히스토리 데이터 분석 중...")
df_year = pd.read_excel(excel_file, sheet_name='19.연도별 자동차 등록현황', header=None)

types_y = df_year.iloc[2, 1:21].ffill().apply(lambda x: str(x).replace('합계', '총계').strip()).values
purposes_y = df_year.iloc[3, 1:21].apply(lambda x: str(x).strip()).values

y_records = []
for _, row in df_year.iloc[4:].iterrows():
    year_val = str(row[0]).strip()
    if not year_val.isdigit(): continue 
    
    for t, p, v in zip(types_y, purposes_y, row[1:21].values):
        y_records.append({
            'year': year_val,
            'type': t,
            'purpose': p,
            'registered_count': int(v) if pd.notna(v) else 0
        })

tidy_yearly = pd.DataFrame(y_records)

dtype_mapping_yearly = {
    'year': String(10), 'type': String(20), 'purpose': String(20), 'registered_count': Integer()
}
tidy_yearly.to_sql(name='car_yearly', con=engine, if_exists='replace', index=False, dtype=dtype_mapping_yearly)

with engine.connect() as con:
    con.execute(text("ALTER TABLE car_yearly ADD PRIMARY KEY (year, type, purpose);"))
    con.commit()
print("   -> 'car_yearly' 테이블 적재 및 기본키(PK) 설정 완료!\n")


# =====================================================================
# [작업 3] 완료 메시지
# =====================================================================
print("▶ [3/3] 모든 작업 완료!")
print("======================================================")
print(" ✅ 데이터베이스(DB) 세팅이 성공적으로 끝났습니다.")
print(" ✅ 이제 터미널에서 'python project1_crawling.py'를 실행하여 크롤링을 진행해 주세요.")
print("======================================================")