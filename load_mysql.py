"""자동차 등록현황 CSV와 FAQ CSV를 MySQL에 저장한다.
기본: python load_mysql.py
FAQ만 적재: python load_mysql.py --only-faq
기존 테이블 구조가 예전과 다르면: python load_mysql.py --reset
"""
from pathlib import Path
import argparse, hashlib, time
import mysql.connector
import pandas as pd
from dotenv import dotenv_values
from mysql.connector import Error

PROJECT_DIR = Path(__file__).resolve().parent
VERIFIED_CSV = PROJECT_DIR / "data" / "자동차_등록현황_통합_검증.csv"
NORMAL_CSV = PROJECT_DIR / "data" / "자동차_등록현황_통합.csv"
DEFAULT_CSV = VERIFIED_CSV if VERIFIED_CSV.exists() else NORMAL_CSV
DEFAULT_FAQ_CSV = PROJECT_DIR / "data" / "faq_data_total.csv"
ENV_FILE = PROJECT_DIR / ".env"
TABLE_NAME = "vehicle_registration_fact"
FAQ_TABLE_NAME = "faq"
BATCH_SIZE = 1000
REQUIRED = ["기준년월","시도","시군구","용도","연료","성별","연령대","규모","등록대수"]
FAQ_REQUIRED = ["company","category_main","category_sub","question","answer"]

def settings():
    return dotenv_values(ENV_FILE)

def connect():
    env = settings()
    try:
        port = int(str(env.get("MYSQL_PORT") or "3306").strip())
    except ValueError as exc:
        raise ValueError(f"MYSQL_PORT는 숫자여야 합니다: {env.get('MYSQL_PORT')!r}") from exc
    if not env.get("MYSQL_USER"):
        raise ValueError(f".env에 MYSQL_USER가 없습니다: {ENV_FILE}")
    if env.get("MYSQL_PASSWORD") is None:
        raise ValueError(f".env에 MYSQL_PASSWORD가 없습니다: {ENV_FILE}")
    return mysql.connector.connect(
        host=str(env.get("MYSQL_HOST") or "127.0.0.1"), port=port,
        user=str(env["MYSQL_USER"]), password=str(env["MYSQL_PASSWORD"]),
        database=str(env.get("MYSQL_DATABASE") or "vehicle_db"),
        use_pure=True, ssl_disabled=True, connection_timeout=30)

def clean(value):
    if pd.isna(value): return "전체"
    value = str(value).strip()
    return value if value else "전체"

def read_csv(path):
    if not path.exists(): raise FileNotFoundError(f"CSV 파일이 없습니다: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig")
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing: raise ValueError("CSV 필수 컬럼이 없습니다: " + ", ".join(missing))
    for col in REQUIRED[:-1]: df[col] = df[col].map(clean)
    df["등록대수"] = pd.to_numeric(df["등록대수"], errors="coerce")
    df = df[df["등록대수"].notna()].copy()
    df["등록대수"] = df["등록대수"].astype("int64")
    return df.drop_duplicates(subset=REQUIRED[:-1], keep="last")

def faq_clean(value):
    """FAQ 문자열의 앞뒤 공백을 제거하고 빈 값은 빈 문자열로 통일한다."""
    if pd.isna(value):
        return ""
    return str(value).strip()

def read_faq_csv(path):
    """FAQ CSV를 읽고 필수 컬럼과 중복 질문을 정리한다."""
    if not path.exists():
        raise FileNotFoundError(f"FAQ CSV 파일이 없습니다: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig")
    missing = [column for column in FAQ_REQUIRED if column not in df.columns]
    if missing:
        raise ValueError("FAQ CSV 필수 컬럼이 없습니다: " + ", ".join(missing))
    for column in FAQ_REQUIRED:
        df[column] = df[column].map(faq_clean)
    df = df[(df["company"] != "") & (df["question"] != "")].copy()
    return df.drop_duplicates(subset=["company", "question"], keep="last")

def data_type(row):
    if row["시군구"] != "전체": return "시군구"
    if row["연료"] != "전체": return "연료"
    if row["성별"] != "전체" or row["연령대"] != "전체": return "성별연령"
    if row["규모"] != "전체": return "규모"
    if row["용도"] != "전체": return "용도"
    return "전체"

def clear_table(conn):
    """검증이 끝난 CSV와 DB가 정확히 같아지도록 기존 행을 모두 비운다."""
    cur = conn.cursor()
    cur.execute(f"TRUNCATE TABLE {TABLE_NAME}")
    conn.commit()
    cur.close()

def clear_faq_table(conn):
    """FAQ 테이블을 CSV와 정확히 맞추기 위해 기존 FAQ 행을 비운다."""
    cur = conn.cursor()
    cur.execute(f"TRUNCATE TABLE {FAQ_TABLE_NAME}")
    conn.commit()
    cur.close()

def record_key(row):
    return hashlib.sha256("|".join(str(row[c]) for c in REQUIRED[:-1]).encode("utf-8")).hexdigest()

def faq_record_key(row):
    """같은 회사의 같은 질문이 중복 적재되지 않도록 고유키를 만든다."""
    source = f"{row['company']}|{row['question']}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()

def ensure_table(conn, reset=False):
    cur = conn.cursor()
    cur.execute(f"SHOW TABLES LIKE '{TABLE_NAME}'")
    exists = cur.fetchone() is not None
    if exists:
        cur.execute(f"SHOW COLUMNS FROM {TABLE_NAME}")
        columns = {row[0] for row in cur.fetchall()}
        expected = {"record_key","data_type","period","sido","sigungu","usage_type",
                    "fuel","gender","age_group","size_group","registration_count"}
        if not expected.issubset(columns):
            if not reset:
                cur.close()
                raise RuntimeError(f"{TABLE_NAME}이 예전 구조입니다. python load_mysql.py --reset 을 실행하세요.")
            cur.execute(f"DROP TABLE {TABLE_NAME}")
            exists = False
    if not exists:
        cur.execute(f"""
            CREATE TABLE {TABLE_NAME} (
                record_key CHAR(64) NOT NULL PRIMARY KEY,
                data_type VARCHAR(20) NOT NULL,
                period CHAR(7) NOT NULL,
                sido VARCHAR(40) NOT NULL,
                sigungu VARCHAR(60) NOT NULL,
                usage_type VARCHAR(40) NOT NULL,
                fuel VARCHAR(80) NOT NULL,
                gender VARCHAR(30) NOT NULL,
                age_group VARCHAR(40) NOT NULL,
                size_group VARCHAR(30) NOT NULL,
                registration_count BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_vehicle_record
                    (period,sido,sigungu,usage_type,fuel,gender,age_group,size_group),
                INDEX ix_period (period), INDEX ix_sido (sido), INDEX ix_type (data_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    conn.commit()
    cur.close()

def ensure_faq_table(conn, reset=False):
    """FAQ 테이블이 없으면 생성하고, 구조가 다르면 오류를 안내한다."""
    cur = conn.cursor()
    cur.execute(f"SHOW TABLES LIKE '{FAQ_TABLE_NAME}'")
    exists = cur.fetchone() is not None
    if exists:
        cur.execute(f"SHOW COLUMNS FROM {FAQ_TABLE_NAME}")
        columns = {row[0] for row in cur.fetchall()}
        expected = {"faq_key", "company", "category_main", "category_sub", "question", "answer"}
        if not expected.issubset(columns):
            if not reset:
                cur.close()
                raise RuntimeError(
                    f"{FAQ_TABLE_NAME} 테이블이 예전 구조입니다. "
                    "python load_mysql.py --only-faq --reset 을 실행하세요."
                )
            cur.execute(f"DROP TABLE {FAQ_TABLE_NAME}")
            exists = False
    if not exists:
        cur.execute(f"""
            CREATE TABLE {FAQ_TABLE_NAME} (
                faq_key CHAR(64) NOT NULL PRIMARY KEY,
                company VARCHAR(50) NOT NULL,
                category_main VARCHAR(100) NOT NULL,
                category_sub VARCHAR(100) NOT NULL,
                question TEXT NOT NULL,
                answer LONGTEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX ix_faq_company (company),
                INDEX ix_faq_category (company, category_main, category_sub)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    conn.commit()
    cur.close()

def make_rows(df):
    rows = []
    for _, row in df.iterrows():
        rows.append((record_key(row), data_type(row), row["기준년월"], row["시도"],
            row["시군구"], row["용도"], row["연료"], row["성별"], row["연령대"],
            row["규모"], int(row["등록대수"])))
    return rows

def make_faq_rows(df):
    rows = []
    for _, row in df.iterrows():
        rows.append((faq_record_key(row), row["company"], row["category_main"],
                     row["category_sub"], row["question"], row["answer"]))
    return rows

def save_batches(conn, rows):
    sql = f"""
        INSERT INTO {TABLE_NAME}
        (record_key,data_type,period,sido,sigungu,usage_type,fuel,gender,age_group,size_group,registration_count)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
          data_type=VALUES(data_type), registration_count=VALUES(registration_count),
          updated_at=CURRENT_TIMESTAMP
    """
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start+BATCH_SIZE]
        for attempt in range(1, 4):
            try:
                conn.ping(reconnect=True, attempts=3, delay=1)
                cur = conn.cursor(); cur.executemany(sql, batch); conn.commit(); cur.close()
                break
            except Error:
                if attempt == 3: raise
                time.sleep(2)
                try: conn.close()
                except Exception: pass
                conn = connect()
        print(f"MySQL 저장 진행: {min(start+BATCH_SIZE,len(rows)):,}/{len(rows):,}행")
    return conn

def save_faq_batches(conn, rows):
    """FAQ를 묶음 단위로 저장하고 기존 질문은 최신 내용으로 갱신한다."""
    sql = f"""
        INSERT INTO {FAQ_TABLE_NAME}
        (faq_key,company,category_main,category_sub,question,answer)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
          category_main=VALUES(category_main),
          category_sub=VALUES(category_sub),
          question=VALUES(question),
          answer=VALUES(answer),
          updated_at=CURRENT_TIMESTAMP
    """
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start+BATCH_SIZE]
        for attempt in range(1, 4):
            try:
                conn.ping(reconnect=True, attempts=3, delay=1)
                cur = conn.cursor()
                cur.executemany(sql, batch)
                conn.commit()
                cur.close()
                break
            except Error:
                if attempt == 3:
                    raise
                time.sleep(2)
                try:
                    conn.close()
                except Exception:
                    pass
                conn = connect()
        print(f"FAQ 저장 진행: {min(start+BATCH_SIZE,len(rows)):,}/{len(rows):,}행")
    return conn

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--faq-input", type=Path, default=DEFAULT_FAQ_CSV)
    parser.add_argument("--only-faq", action="store_true",
                        help="자동차 등록현황은 건너뛰고 FAQ만 저장")
    parser.add_argument("--skip-faq", action="store_true",
                        help="FAQ는 건너뛰고 자동차 등록현황만 저장")
    parser.add_argument("--reset", action="store_true",
                        help="기존 구조가 다른 자동차 또는 FAQ 테이블을 삭제하고 새로 생성")
    parser.add_argument("--replace", action="store_true",
                        help="기존 자동차 등록현황 행을 비운 뒤 CSV 전체를 다시 저장")
    parser.add_argument("--replace-faq", action="store_true",
                        help="기존 FAQ 행을 비운 뒤 FAQ CSV 전체를 다시 저장")
    args = parser.parse_args()
    if args.only_faq and args.skip_faq:
        parser.error("--only-faq와 --skip-faq는 동시에 사용할 수 없습니다.")

    conn = connect()
    try:
        if not args.only_faq:
            print(f"자동차 CSV 읽는 중: {args.input}")
            df = read_csv(args.input)
            print(f"자동차 CSV 행 수: {len(df):,}")
            ensure_table(conn, reset=args.reset)
            if args.replace:
                print("기존 자동차 등록현황 행을 비우고 CSV로 교체합니다.")
                clear_table(conn)
            conn = save_batches(conn, make_rows(df))
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
            print(f"자동차 등록현황 저장 완료: {cur.fetchone()[0]:,}행")
            cur.close()

        if not args.skip_faq:
            print(f"FAQ CSV 읽는 중: {args.faq_input}")
            faq_df = read_faq_csv(args.faq_input)
            print(f"FAQ CSV 행 수: {len(faq_df):,}")
            ensure_faq_table(conn, reset=args.reset)
            if args.replace_faq:
                print("기존 FAQ 행을 비우고 FAQ CSV로 교체합니다.")
                clear_faq_table(conn)
            conn = save_faq_batches(conn, make_faq_rows(faq_df))
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {FAQ_TABLE_NAME}")
            print(f"FAQ 저장 완료: {cur.fetchone()[0]:,}행")
            cur.close()
    finally:
        conn.close()

if __name__ == "__main__":
    try: main()
    except Exception as exc:
        print("MySQL 저장 실패:"); print(exc)

