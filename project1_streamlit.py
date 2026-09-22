import os
import streamlit as st
import pandas as pd
import pymysql
import plotly.express as px
from dotenv import load_dotenv

# .env 로드
load_dotenv()
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Noto Sans KR', sans-serif !important;
        }
        h1, h2, h3 { color: #002C5F !important; }
        [data-testid="stSidebar"] { background-color: #F4F6F9; }
        .info-card {
            padding: 20px;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            border-top: 5px solid #007FA8;
            margin-bottom: 20px;
        }
        .info-card h4 { color: #002C5F; margin-top: 0; font-weight: 700; }
        .info-card p { color: #555555; font-size: 15px; line-height: 1.6; }
        .block-container { padding-top: 2rem; }
        </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def init_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

@st.cache_data
def load_data(_conn, query_or_table):
    if query_or_table.strip().lower().startswith("select"):
        query = query_or_table
    else:
        query = f"SELECT * FROM {query_or_table}"
        
    with _conn.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()
    return pd.DataFrame(result)

def main():
    st.set_page_config(page_title="자동차 통합 정보 포털", page_icon="🚘", layout="wide")
    apply_custom_css()
    
    st.sidebar.title("🧭 네비게이션")
    page = st.sidebar.radio("메뉴를 선택하세요", ["🏠 메인 개요 (Home)", "📊 자동차 등록현황 대시보드", "💬 현대/기아 FAQ 검색"])
    
    if page == "🏠 메인 개요 (Home)":
        st.title("대한민국 자동차 통합 정보 포털 🚘")
        st.markdown("<p style='font-size: 18px; color: #666;'>국내 자동차 등록 통계부터 주요 브랜드의 고객지원 정보까지 한 곳에서 확인하세요.</p>", unsafe_allow_html=True)
        
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="info-card">
                <h4>📊 자동차 등록현황 대시보드</h4>
                <p>국토교통부 공공데이터를 기반으로 대한민국 자동차 등록 현황을 시각화합니다.<br>
                연도별 추이, 동급 차종별 비교, 그리고 지역별 교통량 비율을 3가지 탭 메뉴를 통해 직관적으로 분석할 수 있습니다.</p>
                <b>👉 왼쪽 사이드바에서 '자동차 등록현황 대시보드'를 클릭하세요.</b>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class="info-card">
                <h4>💬 현대/기아 FAQ 스마트 검색</h4>
                <p>현대자동차와 기아의 공식 웹사이트에서 실시간으로 수집된 방대한 고객지원(FAQ) 데이터를 제공합니다.<br>
                원하는 기업과 카테고리를 선택하면, 차량 구매, 정비, 시스템 업데이트 등에 대한 정확한 답변을 빠르게 열람할 수 있습니다.</p>
                <b>👉 왼쪽 사이드바에서 '현대/기아 FAQ 검색'을 클릭하세요.</b>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br><br><br><center><p style='color: #aaaaaa;'>© 2026 Korea Car Data Intelligence Dashboard. All rights reserved.</p></center>", unsafe_allow_html=True)
        
    elif page == "📊 자동차 등록현황 대시보드":
        st.title("🚗 자동차 등록현황 대시보드")
        
        try:
            conn = init_connection()
            df_type = load_data(conn, "car_by_type_v2")
            df_year = load_data(conn, "car_by_year_v2")
            df_region = load_data(conn, "car_by_region")
            
            chart_menu = st.radio(
                "조회할 통계 항목을 선택하세요:",
                ["연도별 차량등록", "차종별 차량등록", "지역별 교통량 비교"],
                horizontal=True
            )
            st.divider()
            
            # [1] 연도별 통계
            if chart_menu == "연도별 차량등록":
                st.subheader("📈 연도별 자동차 등록 추이")
                if not df_year.empty:
                    df_year_total = df_year[df_year['용도'] == '계'].copy()
                    df_year_total = df_year_total.sort_values(by=['차종', '년도'])
                    df_year_total['전년도_등록대수'] = df_year_total.groupby('차종')['등록대수'].shift(1)
                    df_year_total['차이_숫자'] = df_year_total['등록대수'] - df_year_total['전년도_등록대수']
                    
                    def format_diff(x):
                        if pd.isna(x): return "비교 불가"
                        elif x > 0: return f"▲ {int(x):,}대 증가"
                        elif x < 0: return f"▼ {abs(int(x)):,}대 감소"
                        else: return "변동 없음"
                            
                    df_year_total['전년 대비 변동'] = df_year_total['차이_숫자'].apply(format_diff)
                    
                    fig_line = px.line(df_year_total, x='년도', y='등록대수', color='차종', markers=True,
                                       hover_data={"년도": True, "등록대수": ":,대", "전년 대비 변동": True, "차종": False})
                    fig_line.update_layout(xaxis_type='category', yaxis=dict(rangemode='nonnegative'))
                    st.plotly_chart(fig_line, use_container_width=True)

            # [2] 차종별 통계 
            elif chart_menu == "차종별 차량등록":
                st.subheader("📊 차종별 상세 등록 현황 (동급 분류 비교)")
                if 'drill_path' not in st.session_state:
                    st.session_state.drill_path = []
                    
                current_path = st.session_state.drill_path
                current_depth = len(current_path) + 1 
                df_filtered = df_type[(df_type['Depth'] == current_depth) & (df_type['Category_Name'] != '총계')]
                for i, parent_name in enumerate(current_path):
                    level_col = f'Level{i+1}'
                    df_filtered = df_filtered[df_filtered[level_col] == parent_name]
                    
                col1, col2 = st.columns([4, 1])
                with col1:
                    path_str = " > ".join(current_path) if current_path else "최상위 분류 (대분류)"
                    st.markdown(f"**현재 탐색 위치:** `{path_str}`")
                with col2:
                    if current_depth > 1:
                        if st.button("⬅️ 상위로 돌아가기"):
                            st.session_state.drill_path.pop()
                            st.rerun()

                if not df_filtered.empty:
                    fig_bar = px.bar(df_filtered, x='Category_Name', y='합계', text_auto='.2s', color='Category_Name')
                    fig_bar.update_traces(showlegend=False)
                    fig_bar.update_layout(xaxis_title="", yaxis_title="등록대수 (합계)", yaxis=dict(rangemode='nonnegative'))
                    event = st.plotly_chart(fig_bar, on_select="rerun", key=f"drill_{current_depth}", use_container_width=True)
                    
                    if event and event.get("selection") and event["selection"].get("points"):
                        clicked_item = event["selection"]["points"][0]["x"]
                        if current_depth < 4:
                            st.session_state.drill_path.append(clicked_item)
                            st.rerun() 
                else:
                    st.warning("이 항목에 대한 하위 데이터가 존재하지 않습니다.")

            # [3] 지역별 통계 
            elif chart_menu == "지역별 교통량 비교":
                st.subheader("🗺️ 전국 시/도별 총 등록대수 비교")
                
                df_sido = df_region[df_region['Depth'] == 1].copy().reset_index(drop=True)
                
                fig_pie1 = px.pie(
                    df_sido, 
                    names='Category_Name', 
                    values='총계',
                    hole=0.3,
                    height=700
                )
                fig_pie1.update_traces(textposition='inside', textinfo='percent+label', textfont_size=15)
                st.plotly_chart(fig_pie1, use_container_width=True)
                
                st.divider()
                st.subheader("🔎 특정 지역 세부 차종 비율 조회")
                sido_list = df_sido['Category_Name'].tolist()
                selected_sido = st.selectbox("상세 비율을 확인할 시/도를 선택하세요:", options=sido_list)
                
                if selected_sido:
                    sido_data = df_sido[df_sido['Category_Name'] == selected_sido].iloc[0]
                    df_sido_detail = pd.DataFrame({
                        '차종': ['승용차', '승합차', '화물차', '특수차'],
                        '등록대수': [sido_data['승용'], sido_data['승합'], sido_data['화물'], sido_data['특수']]
                    })
                    
                    fig_pie2 = px.pie(
                        df_sido_detail,
                        names='차종',
                        values='등록대수',
                        title=f"[{selected_sido}] 승용/승합/화물/특수 차량 비율",
                        hole=0.4,
                        height=500
                    )
                    fig_pie2.update_traces(textposition='inside', textinfo='percent+label', textfont_size=14)
                    st.plotly_chart(fig_pie2, use_container_width=True)

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

    elif page == "💬 현대/기아 FAQ 검색":
        st.title("💬 기업별 FAQ 스마트 검색")
        st.write("크롤링된 데이터를 기반으로 궁금하신 카테고리의 답변을 단계별로 확인하세요.")
        
        try:
            conn = init_connection()
            df_companies = load_data(conn, "SELECT DISTINCT company FROM faq ORDER BY company")
            
            if not df_companies.empty and 'company' in df_companies.columns:
                companies = ["기업을 선택하세요"] + df_companies['company'].tolist()
                selected_company = st.selectbox("1. 기업 선택", options=companies)
                
                if selected_company != "기업을 선택하세요":
                    query_main = f"SELECT DISTINCT category_main FROM faq WHERE company = '{selected_company}' ORDER BY category_main"
                    df_main = load_data(conn, query_main)
                    main_categories = ["카테고리를 선택하세요"] + df_main['category_main'].tolist()
                    
                    selected_main = st.selectbox("2. 카테고리 선택", options=main_categories)
                    
                    if selected_main != "카테고리를 선택하세요":
                        st.divider()
                        st.subheader(f"[{selected_company}] {selected_main} FAQ 목록")
                        
                        query_faq = f"""
                            SELECT question, answer 
                            FROM faq 
                            WHERE company = '{selected_company}' 
                            AND category_main = '{selected_main}'
                        """
                        df_faq = load_data(conn, query_faq)
                        
                        if not df_faq.empty:
                            for index, row in df_faq.iterrows():
                                with st.expander(f"Q. {row['question']}"):
                                    st.write(row['answer'])
                        else:
                            st.info("해당 분류에 등록된 FAQ가 없습니다.")
            else:
                st.warning("FAQ 데이터가 존재하지 않습니다. 크롤러를 실행하여 데이터를 적재해 주세요.")
                
        except Exception as e:
            st.error(f"데이터베이스 조회 중 오류가 발생했습니다: {e}")

if __name__ == '__main__':
    main()