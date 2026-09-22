import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수에서 DB 정보 가져오기
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = os.getenv('DB_PORT')

# 1. 정리된 3개의 CSV 파일 로드
df_type = pd.read_csv('car_registration_by_type_2.csv')
df_year = pd.read_csv('car_registration_by_year_2.csv')
df_region = pd.read_csv('car_registration_by_region.csv')

# 2. 데이터 적재
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

df_type.to_sql(name='car_by_type_v2', con=engine, if_exists='replace', index=False)
df_year.to_sql(name='car_by_year_v2', con=engine, if_exists='replace', index=False)
df_region.to_sql(name='car_by_region', con=engine, if_exists='replace', index=False)

print("✅ 3가지 통계 데이터가 성공적으로 데이터베이스에 저장되었습니다.")