import pandas as pd
import pymysql
from sqlalchemy import create_engine

# 1. 정리된 3개의 CSV 파일 로드
df_type = pd.read_csv('car_registration_by_type_2.csv')
df_year = pd.read_csv('car_registration_by_year_2.csv')
df_region = pd.read_csv('car_registration_by_region.csv')

# 2. MySQL 접속 정보 설정
DB_USER = 'root'
DB_PASSWORD = '1234' # 사용하시는 비밀번호로 수정
DB_HOST = '127.0.0.1'
DB_PORT = 3306
DB_NAME = 'korea_car'

# 3. 데이터 적재
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

df_type.to_sql(name='car_by_type_v2', con=engine, if_exists='replace', index=False)
df_year.to_sql(name='car_by_year_v2', con=engine, if_exists='replace', index=False)
df_region.to_sql(name='car_by_region', con=engine, if_exists='replace', index=False)

print("✅ 3가지 통계 데이터가 성공적으로 데이터베이스에 저장되었습니다.")