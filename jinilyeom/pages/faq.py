import streamlit as st
import pandas as pd
import pymysql

from components.faq_card import render_faq_card

def load_hyundai_faq():
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "7276",
        "database": "hyundai_db",
        "port": 3306,
        "charset": "utf8mb4"
    }

    try:
        conn = pymysql.connect(**db_config)
        query = "SELECT id, brand, category, page, question, answer FROM hyundai_faq"
        
        df = pd.read_sql(query, conn)
        conn.close()

        return df
    except Exception as e:
        st.error(f"현대 DB 데이터 로드 실패: {e}")
        return pd.DataFrame(columns=["id", "brand", "category", "page", "question", "answer"])

def load_kia_faq():
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "7276",
        "database": "kia_db",
        "port": 3306,
        "charset": "utf8mb4"
    }

    try:
        conn = pymysql.connect(**db_config)
        query = "SELECT id, brand, category, page, question, answer FROM kia_faq"
        
        df = pd.read_sql(query, conn)
        conn.close()

        return df
    except Exception as e:
        st.error(f"기아 DB 데이터 로드 실패: {e}")
        return pd.DataFrame(columns=["id", "brand", "category", "page", "question", "answer"])

def load_faq_data(brand = "현대"):
    if brand == "기아":
        return load_kia_faq()

    return load_hyundai_faq()

def render_faq_detail(df, selected_id):
    row = df[df["id"] == selected_id]

    if row.empty:
        st.session_state.faq_selected_id = None
        st.rerun()

    row = row.iloc[0]

    if st.button("← FAQ 목록으로"):
        st.session_state.faq_selected_id = None
        st.rerun()

    st.markdown(f"### {row['brand']}")
    st.caption(row["category"])

    st.header(row["question"])

    st.divider()

    st.markdown("#### Q.")
    st.write(row["question"])

    st.markdown("#### A.")
    st.write(row["answer"])

    st.divider()

    st.markdown("**출처**")
    st.write(row["brand"])

# FAQ
st.title("FAQ")
st.caption("현대자동차와 기아자동차의 자주하는 질문을 찾아보세요.")

brand = st.segmented_control(
    "제조사",
    ["현대", "기아"],
    default = "현대"
)

df = load_faq_data(brand)

if "faq_selected_id" not in st.session_state:
    st.session_state.faq_selected_id = None

selected_id = st.session_state.faq_selected_id

if selected_id is not None:
    render_faq_detail(df, selected_id)

categories = df["category"].unique().tolist()
category_default = None
if "차량구매" in categories:
    category_default = "차량구매"
elif "차량 구매" in categories:
    category_default = "차량 구매"
elif categories:
    category_default = categories[0]

category = st.segmented_control(
    "카테고리",
    categories,
    default = category_default,
    key = f"category_{brand}"
)

filtered = df[df["category"] == category]

st.caption(f"검색 결과 {len(filtered)}건")

if filtered.empty:
    st.info("검색 결과가 없습니다.")

for _, row in filtered.iterrows():
    render_faq_card(row)