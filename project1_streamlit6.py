"""자동차 등록 현황과 기업별 FAQ 대시보드.

실행: python -m streamlit run project1_streamlit4_updated.py
MySQL 환경변수가 설정되면 DB를 사용하고, 연결할 수 없으면 같은 폴더의 CSV를 사용합니다.
"""
from pathlib import Path
import os

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    import pymysql
except ImportError:
    pymysql = None
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

st.set_page_config(page_title="자동차 등록·기업 FAQ", layout="wide")
BASE = Path(__file__).resolve().parent
# 수정: 새 DB의 등록 상세·연도 테이블명으로 연결합니다. 지역과 차종은 같은 상세 테이블을 집계합니다.
TABLES = {"region": "car_registration", "type": "car_registration", "year": "car_yearly", "faq": "faq"}
FILES = {
    "region": ["car_registration_tidy.csv", "car_registration_tidy (1).csv"],
    "type": ["car_registration_tidy.csv", "car_registration_tidy (1).csv"],
    "year": ["car_yearly_tidy.csv", "car_yearly_tidy (1).csv"],
    "faq": ["faq_data_total.csv", "faq_data_total (1).csv"],
}
NEEDED = {"region": ["city", "year", "month", "type_l1", "type_l2", "type_l3", "type_l4", "registered_count"],
          "type": ["city", "year", "month", "type_l1", "type_l2", "type_l3", "type_l4", "registered_count"],
          "year": ["year", "type", "purpose", "registered_count"],
          "faq": ["company", "category_main", "question", "answer"]}
PALETTE = ["#176B87", "#43A6B8", "#F2A65A", "#586F91", "#7D8E83"]


# 수정: 내용보다 앞서는 큰 홈 화면을 줄이고, 가독성 높은 카드와 차트 색상을 통일했습니다.
st.markdown("""
<style>
  .block-container {max-width: 1250px; padding-top: 1.5rem; padding-bottom: 3rem;}
  h1, h2, h3 {color: #12344A; letter-spacing: -.02em;}
  [data-testid="stMetric"] {background: #F2F7F9; border: 1px solid #DBE9EE;
    border-radius: 14px; padding: 12px 18px;}
  [data-testid="stSidebar"] {background: #F5F8FA;}
  .brand-kicker {font-size: .75rem; font-weight: 750; letter-spacing: .18em;
    color: #176B87; margin: .2rem 0 .35rem;}
  .brand-rule {height: 3px; width: 52px; background: #176B87;
    border-radius: 2px; margin: .85rem 0 1.35rem;}
  .side-brand {font-size: 1.05rem; font-weight: 800; letter-spacing: .08em;
    color: #12344A; margin: .3rem 0 .15rem;}
  .side-sub {font-size: .72rem; letter-spacing: .13em;
    color: #69808C; margin-bottom: 1.3rem;}
  /* 수정: 등록 현황 탭과 FAQ 탭의 용도를 시각적으로 구분합니다. */
  div[data-testid="stTabs"] [role="tab"]:nth-child(5) {
    border-left: 1px solid #D5E0E6; margin-left: 18px; padding-left: 22px;
  }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def query_table(table: str, config: tuple) -> pd.DataFrame:
    # 수정: 공유 DB 연결 객체를 캐시하지 않고 조회마다 연결·종료합니다.
    # 테이블명은 코드에 정의된 허용 목록의 값만 사용합니다.
    conn = pymysql.connect(host=config[0], user=config[1], password=config[2],
                           database=config[3], charset="utf8mb4",
                           cursorclass=pymysql.cursors.DictCursor,
                           connect_timeout=3, read_timeout=10)
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM `{table}`")
            return pd.DataFrame(cursor.fetchall())
    finally:
        conn.close()


@st.cache_data
def read_csv(path: str) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV 인코딩은 UTF-8 또는 CP949로 저장해 주세요.")


def prepare(df: pd.DataFrame, key: str) -> pd.DataFrame:
    # 수정: 새 tidy 스키마를 기존 화면이 읽는 구조로 변환해 차트와 탐색 코드를 유지합니다.
    missing = set(NEEDED[key]) - set(df.columns)
    if missing:
        raise ValueError(f"{key} 데이터에 필요한 컬럼이 없습니다: {', '.join(sorted(missing))}")
    result = df.copy()
    if key == "faq":
        return result
    result["registered_count"] = pd.to_numeric(
        result["registered_count"].astype(str).str.replace(",", "", regex=False), errors="coerce")
    result = result.dropna(subset=["registered_count"])
    if key == "year":
        result["년도"] = pd.to_numeric(result["year"], errors="coerce")
        result["차종"] = result["type"].replace({"총계": "합계"})
        result["용도"] = result["purpose"]
        result["등록대수"] = result["registered_count"]
        return result[["년도", "차종", "용도", "등록대수"]].dropna(subset=["년도"])

    # 수정: 여러 연월이 저장돼도 최신 한 시점만 사용하여 등록 대수가 섞이지 않게 합니다.
    result["year"] = pd.to_numeric(result["year"], errors="coerce")
    result["month"] = pd.to_numeric(result["month"], errors="coerce")
    result = result.dropna(subset=["year", "month", "city", "type_l1"])
    if result.empty:
        raise ValueError("유효한 등록 연월·지역 자료가 없습니다.")
    latest_year, latest_month = result[["year", "month"]].drop_duplicates().sort_values(
        ["year", "month"]).iloc[-1]
    result = result[(result["year"] == latest_year) & (result["month"] == latest_month)]
    snapshot = f"{int(latest_year)}.{int(latest_month):02d}"
    if key == "region":
        totals = result.pivot_table(index="city", columns="type_l1", values="registered_count",
                                    aggfunc="sum", fill_value=0)
        for kind in ("승용", "승합", "화물", "특수"):
            if kind not in totals:
                totals[kind] = 0
        totals = totals[["승용", "승합", "화물", "특수"]].reset_index().rename(columns={"city": "Category_Name"})
        totals["총계"] = totals[["승용", "승합", "화물", "특수"]].sum(axis=1)
        totals["Depth"] = 1
        totals["Level1"] = totals["Category_Name"]
        # 새 자료에는 시군구가 없으므로 같은 위치의 상세 표에는 해당 지역의 유형별 합계를 표시합니다.
        detail = result.groupby(["city", "type_l1", "type_l2"], as_index=False)["registered_count"].sum()
        detail["Level1"] = detail["city"]
        detail["Category_Name"] = detail["type_l1"] + " · " + detail["type_l2"]
        detail["총계"] = detail["registered_count"]
        detail["Depth"] = 2
        combined = pd.concat([totals, detail[["Category_Name", "Depth", "Level1", "총계"]]], ignore_index=True)
        combined.attrs["snapshot"] = snapshot
        return combined

    # 각 단계는 4단계 상세 행에서 한 번만 집계합니다. 서로 다른 Depth를 다시 합산하지 않습니다.
    paths = ["type_l1", "type_l2", "type_l3", "type_l4"]
    all_cities = sorted(result["city"].astype(str).unique().tolist())
    levels = []
    for depth in (1, 2, 3, 4):
        group_cols = paths[:depth]
        grouped = result.groupby(group_cols + ["city"], as_index=False)["registered_count"].sum()
        wide = grouped.pivot_table(index=group_cols, columns="city", values="registered_count",
                                   aggfunc="sum", fill_value=0).reset_index()
        for city in all_cities:
            if city not in wide:
                wide[city] = 0
        wide["합계"] = wide[all_cities].sum(axis=1)
        wide["Depth"] = depth
        wide["Category_Name"] = wide[paths[depth-1]]
        for index in range(1, 5):
            wide[f"Level{index}"] = wide[paths[index-1]] if index <= depth else None
        levels.append(wide[["Category_Name", "Depth", "Level1", "Level2", "Level3", "Level4", "합계"] + all_cities])
    combined = pd.concat(levels, ignore_index=True)
    combined.attrs["snapshot"] = snapshot
    return combined


def get_data(key: str, use_db: bool, config: tuple):
    # 수정: 기존 MySQL을 우선 사용하고 연결 실패 시 로컬 CSV로 이어집니다.
    if use_db and pymysql is not None:
        try:
            db_data = prepare(query_table(TABLES[key], config), key)
            # 수정: FAQ 테이블에 쉐보레 적재가 아직 반영되지 않았다면 제공된 통합 CSV로 보완합니다.
            if key == "faq" and "쉐보레" not in db_data["company"].astype(str).unique():
                for filename in FILES["faq"]:
                    for path in (BASE / filename, BASE / "data" / filename):
                        if path.is_file():
                            supplement = prepare(read_csv(str(path)), "faq")
                            db_data = pd.concat([db_data, supplement], ignore_index=True).drop_duplicates()
                            return db_data, "MySQL + FAQ CSV"
            return db_data, "MySQL"
        except Exception as exc:
            st.sidebar.caption(f"{key} DB 조회 실패 → CSV 사용 ({type(exc).__name__})")
    for filename in FILES[key]:
        for path in (BASE / filename, BASE / "data" / filename):
            if path.is_file():
                try:
                    return prepare(read_csv(str(path)), key), f"CSV · {path.name}"
                except Exception as exc:
                    st.sidebar.warning(f"{path.name}: {exc}")
    return pd.DataFrame(), "자료 없음"


def download(df: pd.DataFrame, filename: str):
    st.download_button("표 다운로드 (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=filename, mime="text/csv")


def bars(df: pd.DataFrame, x: str, y: str, horizontal=False):
    fig = (px.bar(df, x=y, y=x, orientation="h", text=y) if horizontal
           else px.bar(df, x=x, y=y, text=y))
    fig.update_traces(marker_color=PALETTE[0], texttemplate="%{text:,.0f}",
                      textposition="outside", cliponaxis=False,
                      hovertemplate="%{x}<br>%{y:,.0f}대<extra></extra>" if not horizontal else None)
    fig.update_layout(template="plotly_white", height=max(350, min(650, len(df)*31+120)),
                      margin=dict(l=10, r=40, t=15, b=35), showlegend=False,
                      xaxis_title=None, yaxis_title=None, font=dict(color="#234255"))
    if horizontal:
        fig.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig, width="stretch")


# 수정: 사이드바의 두 라디오 버튼으로 등록 현황과 FAQ 화면을 구분합니다.
MENU = ["한눈에 보기", "연도별 추이", "차종별 구성", "지역별 현황", "FAQ 찾기"]
if "page_group" not in st.session_state:
    st.session_state.page_group = MENU[0]
if "registration_choice" not in st.session_state:
    st.session_state.registration_choice = MENU[0]
if "faq_choice" not in st.session_state:
    st.session_state.faq_choice = None


def select_registration():
    if st.session_state.registration_choice == MENU[0]:
        st.session_state.page_group = MENU[0]
        st.session_state.faq_choice = None


def select_faq():
    if st.session_state.faq_choice == MENU[4]:
        st.session_state.page_group = MENU[4]
        st.session_state.registration_choice = None


# 수정: 이모지 대신 문자 기반 브랜드 표식과 절제된 색상·간격을 사용합니다.
st.sidebar.markdown('<div class="side-brand">CAR DATA</div><div class="side-sub">INSIGHTS PLATFORM</div>', unsafe_allow_html=True)
st.sidebar.header("화면 이동")
# 수정: 등록 현황은 한눈에 보기만 사이드바에 남깁니다. 세부 화면은 본문의 상단 탭에서 엽니다.
st.sidebar.caption("자동차 등록 현황")
st.sidebar.radio("등록 화면", [MENU[0]], index=None, key="registration_choice",
                 label_visibility="collapsed", on_change=select_registration)
st.sidebar.divider()
st.sidebar.caption("기업별 FAQ")
st.sidebar.radio("FAQ 화면", [MENU[4]], index=None, key="faq_choice",
                 label_visibility="collapsed", on_change=select_faq)

config = tuple(os.getenv(k, "") for k in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"))
use_db = bool(all(config))
data = {}
sources = {}
for key in TABLES:
    data[key], sources[key] = get_data(key, use_db, config)

# 수정: 등록 화면에는 등록 탭 4개만, FAQ 화면에는 FAQ 탭만 표시합니다.
st.markdown('<div class="brand-kicker">CAR DATA / INSIGHTS</div>', unsafe_allow_html=True)
if st.session_state.page_group == MENU[0]:
    st.title("자동차 등록 현황")
    st.markdown('<div class="brand-rule"></div>', unsafe_allow_html=True)
    st.caption("지역별 규모, 차종 구성, 연도별 변화를 한 화면에서 살펴보세요.")
    overview, trend, types, regions = st.tabs(MENU[:4], key="registration_tabs", on_change="rerun")
else:
    st.title("기업별 FAQ")
    st.markdown('<div class="brand-rule"></div>', unsafe_allow_html=True)
    questions, = st.tabs([MENU[4]])

if st.session_state.page_group == MENU[0]:
    with overview:
        st.subheader("등록 현황 한눈에 보기")
        region = data["region"]
        vehicle = data["type"]
        annual = data["year"]
        top = region[region["Depth"] == 1] if not region.empty else pd.DataFrame()
        kind_top = vehicle[vehicle["Depth"] == 1] if not vehicle.empty else pd.DataFrame()
        latest = annual[(annual["차종"] == "합계") & (annual["용도"] == "계")].sort_values("년도") if not annual.empty else pd.DataFrame()
        # 수정: 한눈에 보기에서는 자동차 등록 지표만 표시합니다.
        m1, m2, m3 = st.columns(3)
        m1.metric("4단계 상세 자료 합계", f"{top['총계'].sum():,.0f}대" if not top.empty else "자료 없음")
        m2.metric("등록 대수 최다 지역", str(top.loc[top["총계"].idxmax(), "Category_Name"]) if not top.empty else "자료 없음")
        m3.metric("연도 자료 최신", f"{int(latest.iloc[-1]['년도'])}년" if not latest.empty else "자료 없음")
        if not kind_top.empty:
            st.subheader("차종별 등록 구성")
            summary = kind_top[["Category_Name", "합계"]].sort_values("합계", ascending=False)
            bars(summary, "Category_Name", "합계")
        # 수정: 새 DB는 4단계 상세 행만 저장하여 원본 엑셀의 전체 총계보다 작습니다.
        if not top.empty:
            st.info(f"등록 상세 자료 기준: {region.attrs.get('snapshot', '기준일 미확인')} · "
                    f"표시 합계 {top['총계'].sum():,.0f}대는 4단계 상세 행의 합계입니다. "
                    "제공된 2026년 8월 원본 엑셀의 전체 총계 26,687,284대와 동일한 범위가 아닙니다.")

    with trend:
        st.subheader("연도별 등록 대수")
        st.caption("차종과 용도를 하나씩 선택합니다. 원본의 ‘합계’와 세부 행을 동시에 더하지 않습니다.")
        df = data["year"]
        if df.empty:
            st.warning("연도 자료를 찾지 못했습니다.")
        else:
            a, b = st.columns(2)
            with a:
                kind = st.selectbox("차종", [x for x in ["합계", "승용", "승합", "화물", "특수"] if x in df["차종"].values])
            with b:
                purpose = st.selectbox("용도", [x for x in ["계", "관용", "자가용", "영업용"] if x in df["용도"].values])
            series = df[(df["차종"] == kind) & (df["용도"] == purpose)][["년도", "등록대수"]].dropna().sort_values("년도")
            if series.empty:
                st.info("선택한 항목의 자료가 없습니다.")
            else:
                current = series.iloc[-1]
                delta = current["등록대수"] - series.iloc[-2]["등록대수"] if len(series) > 1 else None
                st.metric(f"{int(current['년도'])}년 · {kind} · {purpose}", f"{current['등록대수']:,.0f}대",
                          f"{delta:+,.0f}대 (전년 대비)" if delta is not None else None)
                fig = px.line(series, x="년도", y="등록대수", markers=True)
                fig.update_traces(line_color=PALETTE[0], line_width=3, marker_size=6)
                fig.update_layout(template="plotly_white", height=420, xaxis_title="년도", yaxis_title="등록 대수")
                st.plotly_chart(fig, width="stretch")
                st.dataframe(series, hide_index=True, width="stretch")
                download(series, "year_trend.csv")

    with types:
        st.subheader("차종별 등록 구성")
        df = data["type"]
        st.caption(f"{df.attrs.get('snapshot', '등록 자료')}의 4단계 상세 행 기준입니다. 원본 엑셀의 전체 총계와 범위가 다릅니다.")
        if df.empty:
            st.warning("차종 자료를 찾지 못했습니다.")
        else:
            # 수정: 차트 클릭 상태 대신 선택 상자를 사용해 현재 탐색 위치를 분명히 보여줍니다.
            top = df[df["Depth"] == 1][["Category_Name", "합계"]].copy()
            top["비중(%)"] = (top["합계"] / top["합계"].sum() * 100).round(1)
            st.dataframe(top, hide_index=True, width="stretch")
            parent = st.selectbox("차종 선택", top["Category_Name"].tolist())
            chosen = df[df["Category_Name"] == parent].iloc[0]
            for depth in (2, 3, 4):
                children = df[(df["Depth"] == depth) & (df[f"Level{depth-1}"] == chosen["Category_Name"])]
                # 수정: 새 tidy 자료에는 '계'와 '외산'이 여러 상위 분류에서 반복되어 전체 경로로 구분합니다.
                if depth >= 3:
                    children = children[children["Level1"] == chosen["Level1"]]
                if depth >= 4:
                    children = children[children["Level2"] == chosen["Level2"]]
                if children.empty:
                    break
                st.caption(f"{chosen['Category_Name']}의 하위 유형")
                bars(children[["Category_Name", "합계"]].sort_values("합계", ascending=False), "Category_Name", "합계", horizontal=True)
                choice = st.selectbox(f"{depth}단계 세부 유형", ["이 단계에서 보기"] + children["Category_Name"].tolist(), key=f"depth_{depth}")
                if choice == "이 단계에서 보기":
                    break
                chosen = children[children["Category_Name"] == choice].iloc[0]
            st.caption(f"선택: {chosen['Category_Name']} · {chosen['합계']:,.0f}대. 상위 합계와 하위 항목을 함께 더하지 않습니다.")
            names = [c for c in df.columns if c not in ["Category_Name", "Depth", "Level1", "Level2", "Level3", "Level4", "합계"]]
            spread = pd.DataFrame({"지역": names, "등록대수": [chosen[c] for c in names]}).dropna().sort_values("등록대수", ascending=False)
            st.markdown("**선택한 유형의 지역 분포**")
            bars(spread, "지역", "등록대수", horizontal=True)

    with regions:
        st.subheader("지역별 등록 현황")
        df = data["region"]
        if df.empty:
            st.warning("지역 자료를 찾지 못했습니다.")
        else:
            # 수정: 16개 지역의 원형 차트 대신 순위 비교가 쉬운 가로 막대를 사용합니다.
            groups = df[df["Depth"] == 1].copy().sort_values("총계", ascending=False)
            if groups.empty:
                st.warning("지역 합계 행(Depth=1)이 없습니다.")
            else:
                st.metric("4단계 상세 자료의 지역별 합계", f"{groups['총계'].sum():,.0f}대")
                st.caption(f"등록 상세 자료 기준: {df.attrs.get('snapshot', '기준일 미확인')} · "
                           "원본의 ‘전남광주’는 하나의 그룹입니다. 시군구 자료는 이 테이블에 없습니다.")
                bars(groups[["Category_Name", "총계"]], "Category_Name", "총계", horizontal=True)
                selected = st.selectbox("상세 지역", groups["Category_Name"].tolist())
                row = groups[groups["Category_Name"] == selected].iloc[0]
                detail = pd.DataFrame({"차종": ["승용", "승합", "화물", "특수"],
                                       "등록대수": [row[c] for c in ["승용", "승합", "화물", "특수"]]})
                left, right = st.columns([1, 1])
                with left:
                    st.markdown(f"**{selected}의 차종 구성**")
                    fig = px.pie(detail, names="차종", values="등록대수", hole=.58,
                                 color="차종", color_discrete_sequence=PALETTE)
                    fig.update_layout(template="plotly_white", showlegend=True,
                                      margin=dict(l=0, r=0, t=10, b=0), height=320)
                    st.plotly_chart(fig, width="stretch")
                with right:
                    st.markdown(f"**{selected}의 세부 차종**")
                    district = df[(df["Depth"] == 2) & (df["Level1"] == selected)][["Category_Name", "총계"]].sort_values("총계", ascending=False)
                    st.dataframe(district, hide_index=True, height=300, width="stretch")
                download(groups[["Category_Name", "총계", "승용", "승합", "화물", "특수"]], "region_summary.csv")

if st.session_state.page_group == MENU[4]:
    with questions:
        # 수정: 기업 목록은 DB/CSV에서 가져오므로 쉐보레가 자동으로 선택 항목에 포함됩니다.
        st.subheader("기업별 FAQ")
        st.caption("기업과 분류를 고르거나 질문을 검색하세요. 원본에 수집일과 출처 URL이 없어 최신 정책은 공식 채널에서 확인해 주세요.")
        df = data["faq"]
        if df.empty:
            st.warning("FAQ 자료를 찾지 못했습니다.")
        else:
            # 수정: 기업→분류를 반드시 순서대로 골라야 했던 흐름을 검색 중심으로 바꿨습니다.
            filtered = df.dropna(subset=["company", "question"]).drop_duplicates().copy()
            a, b = st.columns(2)
            with a:
                company = st.selectbox("기업", ["전체"] + sorted(filtered["company"].astype(str).unique()))
            if company != "전체":
                filtered = filtered[filtered["company"] == company]
            with b:
                category = st.selectbox("분류", ["전체"] + sorted(filtered["category_main"].dropna().astype(str).unique()))
            if category != "전체":
                filtered = filtered[filtered["category_main"] == category]
            keyword = st.text_input("질문 검색", placeholder="예: 계약, 정비, 시승")
            if keyword.strip():
                filtered = filtered[filtered["question"].astype(str).str.contains(keyword.strip(), case=False, regex=False, na=False)]
            st.metric("검색 결과", f"{len(filtered):,}건")
            if filtered.empty:
                st.info("검색 결과가 없습니다. 다른 키워드를 입력해 보세요.")
            for _, row in filtered.head(50).iterrows():
                with st.expander(f"[{row['company']}] {row['question']}"):
                    st.write(row["answer"] if pd.notna(row["answer"]) else "답변 없음")
                    st.caption(f"분류: {row['category_main']}")
            if len(filtered) > 50:
                st.caption("처음 50건만 화면에 표시합니다. 전체 검색 결과는 CSV로 내려받을 수 있습니다.")
            download(filtered, "faq_search.csv")
