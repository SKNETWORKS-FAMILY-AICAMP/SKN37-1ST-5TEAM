import os
import streamlit as st
import pandas as pd
import pymysql
import plotly.express as px
from dotenv import load_dotenv

def apply_custom_css():
    st.markdown("""
        <style>
        /* 부드러운 둥근 폰트 'Jua' 적용 (제목 및 주요 버튼에 적용) */
        @import url('https://fonts.googleapis.com/css2?family=Jua&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
        
        html, body, [class*="css"] { 
            font-family: 'Noto Sans KR', sans-serif !important; 
        }
        
        h1, h2, h3, .sidebar-content {
            font-family: 'Jua', sans-serif !important;
        }

        /* 부드러운 파스텔 배경 */
        .stApp { background-color: #FFF9F9; }
        
        /* 둥글고 입체적인 카드 디자인 */
        .cute-card { 
            padding: 25px; 
            background-color: #ffffff; 
            border-radius: 25px; 
            box-shadow: 0 8px 20px rgba(255, 182, 193, 0.3); 
            border: 3px solid #FFE4E1;
            margin-bottom: 15px; 
            min-height: 250px;
            transition: transform 0.2s;
        }
        .cute-card:hover { transform: translateY(-5px); }
        .cute-card h4 { color: #FF7F50; font-size: 22px; margin-top: 0; font-family: 'Jua', sans-serif !important; }
        .cute-card p { color: #555555; font-size: 16px; line-height: 1.6; }
        
        /* 버튼 스타일 둥글게 */
        div[data-testid="stButton"] button {
            border-radius: 20px !important;
            background-color: #FFB6C1 !important;
            color: white !important;
            border: none !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            height: 50px;
        }
        div[data-testid="stButton"] button:hover {
            background-color: #FF8C00 !important;
            box-shadow: 0 4px 10px rgba(255, 140, 0, 0.3);
        }
        </style>
    """, unsafe_allow_html=True)

load_dotenv()
@st.cache_resource
def init_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'), user=os.getenv('DB_USER', 'root'), 
        password=os.getenv('DB_PASSWORD', 'your_password'), database=os.getenv('DB_NAME', 'testdb1'), 
        cursorclass=pymysql.cursors.DictCursor
    )

@st.cache_data
def load_data(_conn, query):
    with _conn.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()
    return pd.DataFrame(result)

# 페이지 이동 콜백
def change_page(page_name):
    st.session_state['menu_selection'] = page_name

def main():
    st.set_page_config(page_title="자동차 통합 정보 포털", page_icon="🚘", layout="wide")
    apply_custom_css()
    
    if 'menu_selection' not in st.session_state:
        st.session_state['menu_selection'] = "🏠 메인 홈"
        
    st.sidebar.title("🧭 네비게이션")
    page = st.sidebar.radio(
        "원하시는 메뉴를 선택해 주세요", 
        ["🏠 메인 홈", "📊 자동차 등록현황 대시보드", "💬 기업별 FAQ 검색"],
        key='menu_selection'
    )
    
    try:
        conn = init_connection()
    except Exception as e:
        st.error("데이터베이스 연결에 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.")
        return

    # ---------------------------------------------------------
    # [페이지 1] 메인 홈
    # ---------------------------------------------------------
    if page == "🏠 메인 홈":
        st.title("대한민국 자동차 통합 정보 포털 🚘")
        st.markdown("<p style='font-size: 18px; color: #666;'>국토교통부 통계 데이터를 바탕으로 직관적인 자동차 등록 현황과 공식 고객지원(FAQ) 정보를 제공합니다.</p>", unsafe_allow_html=True)
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div class="cute-card">
                <h4>📊 자동차 등록현황 대시보드</h4>
                <p>전국의 자동차 등록 현황을 다양한 차트로 확인하실 수 있습니다.<br><br>
                ✔️ <strong>연도별 트렌드 분석:</strong> 전년도 대비 증감 및 장기 추이<br>
                ✔️ <strong>차종별 상세 비교:</strong> 단계별 클릭을 통한 상세 현황 탐색<br>
                ✔️ <strong>지역별 현황:</strong> 전국 시/도별 자동차 등록 비율</p>
            </div>
            """, unsafe_allow_html=True)
            st.button("👉 대시보드 바로가기", on_click=change_page, args=("📊 자동차 등록현황 대시보드",), use_container_width=True)
            
        with col2:
            st.markdown("""
            <div class="cute-card">
                <h4>💬 기업별 FAQ 스마트 검색</h4>
                <p>현대, 기아, 쉐보레 등 주요 자동차 브랜드의 공식 고객지원 데이터를 모았습니다.<br><br>
                기업과 원하시는 카테고리를 선택하시면 평소 궁금하셨던 질문과 답변을 빠르게 찾아보실 수 있습니다.</p>
            </div>
            """, unsafe_allow_html=True)
            st.button("👉 FAQ 검색 바로가기", on_click=change_page, args=("💬 기업별 FAQ 검색",), use_container_width=True)

    # ---------------------------------------------------------
    # [페이지 2] 대시보드
    # ---------------------------------------------------------
    elif page == "📊 자동차 등록현황 대시보드":
        st.title("🚗 자동차 등록현황 대시보드")
        chart_menu = st.radio("조회하실 통계 항목을 선택해 주세요:", ["📈 연도별 등록 추이", "📊 차종별 상세 비교", "🗺️ 지역별 등록 현황"], horizontal=True)
        st.divider()
        
        # [2-1] 연도별 등록 추이
        if chart_menu == "📈 연도별 등록 추이":
            st.subheader("📈 연도별 자동차 등록 추이 (2007년 ~ 현재)")
            st.write("그래프의 점 위에 마우스를 올리시면 전년도 대비 증가/감소 수치를 확인하실 수 있습니다.")
            
            query = "SELECT year AS 년도, type AS 차종, registered_count AS 등록대수 FROM car_yearly WHERE purpose = '계' AND type != '총계'"
            df_year = load_data(conn, query)
            if not df_year.empty:
                df_year = df_year.sort_values(by=['차종', '년도'])
                df_year['전년도_등록대수'] = df_year.groupby('차종')['등록대수'].shift(1)
                df_year['증감대수'] = df_year['등록대수'] - df_year['전년도_등록대수']
                
                def format_diff(x):
                    if pd.isna(x): return "비교 불가"
                    elif x > 0: return f"▲ {int(x):,}대 증가"
                    elif x < 0: return f"▼ {abs(int(x)):,}대 감소"
                    else: return "변동 없음"
                df_year['전년 대비 변화'] = df_year['증감대수'].apply(format_diff)
                
                fig_line = px.line(df_year, x='년도', y='등록대수', color='차종', markers=True, hover_data={"년도": True, "등록대수": ":,대", "전년 대비 변화": True, "차종": False})
                fig_line.update_layout(xaxis_type='category', yaxis=dict(rangemode='nonnegative'))
                st.plotly_chart(fig_line, use_container_width=True)

        # [2-2] 차종별 상세 비교
        elif chart_menu == "📊 차종별 상세 비교":
            st.subheader("📊 차종별 상세 등록 현황 비교")
            st.write("궁금하신 차종의 막대그래프를 클릭하시면, 차량 형태부터 배기량까지 단계별로 상세한 통계를 확인하실 수 있습니다.")
            
            query = "SELECT type_l1, type_l2, type_l3, type_l4, SUM(registered_count) as 등록대수 FROM car_registration GROUP BY type_l1, type_l2, type_l3, type_l4"
            df_all = load_data(conn, query)
            
            for lvl in ['l1', 'l2', 'l3']:
                if lvl not in st.session_state: st.session_state[lvl] = None

            col1, col2 = st.columns([4, 1])
            with col1:
                path = "전체 차종"
                if st.session_state.l1: path += f" > {st.session_state.l1}"
                if st.session_state.l2: path += f" > {st.session_state.l2}"
                if st.session_state.l3: path += f" > {st.session_state.l3}"
                st.markdown(f"**현재 탐색 중인 분류:** `{path}`")
            with col2:
                if st.session_state.l1 or st.session_state.l2 or st.session_state.l3:
                    if st.button("⬅️ 이전 단계로 돌아가기"):
                        if st.session_state.l3: st.session_state.l3 = None
                        elif st.session_state.l2: st.session_state.l2 = None
                        else: st.session_state.l1 = None
                        st.rerun()

            if not df_all.empty:
                if st.session_state.l1 is None:
                    df_agg = df_all.groupby('type_l1', as_index=False)['등록대수'].sum()
                    fig = px.bar(df_agg, x='type_l1', y='등록대수', text_auto='.2s', color='type_l1', title="1단계: 원하시는 차종을 선택해 주세요 (클릭)")
                    event = st.plotly_chart(fig, on_select="rerun", key="c1", use_container_width=True)
                    if event and event.get("selection") and event["selection"].get("points"):
                        st.session_state.l1 = event["selection"]["points"][0]["x"]; st.rerun()
                elif st.session_state.l2 is None:
                    df_agg = df_all[df_all['type_l1'] == st.session_state.l1].groupby('type_l2', as_index=False)['등록대수'].sum()
                    fig = px.bar(df_agg, x='type_l2', y='등록대수', text_auto='.2s', color='type_l2', title=f"2단계: [{st.session_state.l1}] 차량 형태별 등록대수 (클릭)")
                    event = st.plotly_chart(fig, on_select="rerun", key="c2", use_container_width=True)
                    if event and event.get("selection") and event["selection"].get("points"):
                        st.session_state.l2 = event["selection"]["points"][0]["x"]; st.rerun()
                elif st.session_state.l3 is None:
                    df_agg = df_all[(df_all['type_l1'] == st.session_state.l1) & (df_all['type_l2'] == st.session_state.l2)].groupby('type_l3', as_index=False)['등록대수'].sum()
                    fig = px.bar(df_agg, x='type_l3', y='등록대수', text_auto='.2s', color='type_l3', title=f"3단계: [{st.session_state.l2}] 제조국가(국산/외산) 비교 (클릭)")
                    event = st.plotly_chart(fig, on_select="rerun", key="c3", use_container_width=True)
                    if event and event.get("selection") and event["selection"].get("points"):
                        st.session_state.l3 = event["selection"]["points"][0]["x"]; st.rerun()
                else:
                    df_agg = df_all[(df_all['type_l1'] == st.session_state.l1) & (df_all['type_l2'] == st.session_state.l2) & (df_all['type_l3'] == st.session_state.l3)].groupby('type_l4', as_index=False)['등록대수'].sum()
                    fig = px.bar(df_agg, x='type_l4', y='등록대수', text_auto='.2s', color='type_l4', title=f"4단계: [{st.session_state.l3}] 세부 배기량 및 모델별 현황")
                    st.plotly_chart(fig, use_container_width=True)

        # [2-3] 지역별 등록 현황
        elif chart_menu == "🗺️ 지역별 등록 현황":
            st.subheader("🗺️ 전국 시/도별 자동차 등록 비율")
            st.write("원하시는 지역의 원형 그래프 조각을 클릭하시면, 해당 지역에 등록된 세부 차종 비율을 확인하실 수 있습니다.")
            query = "SELECT city, type_l1, SUM(registered_count) as 등록대수 FROM car_registration GROUP BY city, type_l1"
            df_region = load_data(conn, query)
            
            if not df_region.empty:
                df_city_total = df_region.groupby('city', as_index=False)['등록대수'].sum()
                fig_pie1 = px.pie(df_city_total, names='city', values='등록대수', hole=0.4)
                event_pie = st.plotly_chart(fig_pie1, on_select="rerun", key="pie_sido", use_container_width=True)
                
                clicked_sido = "서울"
                if event_pie and event_pie.get("selection") and event_pie["selection"].get("points"):
                    clicked_point = event_pie["selection"]["points"][0]
                    clicked_sido = clicked_point["customdata"][0] if "customdata" in clicked_point else df_city_total.iloc[clicked_point["point_index"]]['city']
                
                selected_sido = st.selectbox("상세 비율을 확인할 시/도를 선택해 주세요:", options=df_city_total['city'].tolist(), index=df_city_total['city'].tolist().index(clicked_sido) if clicked_sido in df_city_total['city'].tolist() else 0)
                if selected_sido:
                    df_sido_detail = df_region[df_region['city'] == selected_sido]
                    fig_pie2 = px.pie(df_sido_detail, names='type_l1', values='등록대수', title=f"[{selected_sido}] 지역 승용/승합/화물/특수 차량 등록 비율", hole=0.5)
                    st.plotly_chart(fig_pie2, use_container_width=True)

    # ---------------------------------------------------------
    # [페이지 3] FAQ
    # ---------------------------------------------------------
    elif page == "💬 기업별 FAQ 검색":
        st.title("💬 기업별 FAQ 스마트 검색")
        st.write("차량 구매나 정비 등 평소 궁금하셨던 내용을 공식 고객지원 데이터에서 빠르게 찾아보세요.")
        try:
            df_companies = load_data(conn, "SELECT DISTINCT company FROM faq ORDER BY company")
            if not df_companies.empty:
                selected_company = st.selectbox("1. 기업 선택", ["기업을 선택해 주세요"] + df_companies['company'].tolist())
                if selected_company != "기업을 선택해 주세요":
                    df_main = load_data(conn, f"SELECT DISTINCT category_main FROM faq WHERE company = '{selected_company}' ORDER BY category_main")
                    selected_main = st.selectbox("2. 카테고리 선택", ["카테고리를 선택해 주세요"] + df_main['category_main'].tolist())
                    
                    if selected_main != "카테고리를 선택해 주세요":
                        st.divider()
                        df_faq = load_data(conn, f"SELECT question, answer FROM faq WHERE company = '{selected_company}' AND category_main = '{selected_main}'")
                        if not df_faq.empty:
                            for _, row in df_faq.iterrows():
                                with st.expander(f"Q. {row['question']}"): 
                                    st.write(f"**A.** {row['answer']}")
        except Exception as e:
            st.error("데이터를 불러오는 중 오류가 발생했습니다.")

if __name__ == '__main__':
    main()