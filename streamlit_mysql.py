"""MySQL 자동차 등록자료를 조회하는 Streamlit 대시보드.

실행: streamlit run streamlit_mysql.py
MySQL 연결에 실패하면 검증 CSV, 운영 CSV 순서로 자동 대체합니다.
"""
from __future__ import annotations

from pathlib import Path
from datetime import date, timedelta
from html import escape
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pymysql
import requests
import streamlit as st
from dotenv import dotenv_values

BASE = Path(__file__).resolve().parent
ENV = dotenv_values(BASE / ".env")
TABLE = "vehicle_registration_fact"
FAQ_TABLE = "faq"
CSV_CANDIDATES = [BASE / "data" / "자동차_등록현황_통합_검증.csv", BASE / "data" / "자동차_등록현황_통합.csv"]
FAQ_CSV = BASE / "data" / "faq_data_total.csv"
CAR_TABS = ["지역별", "차종별", "연료별", "성별"]
FAQ_TABS = ["통합", "현대", "기아", "쉐보레"]
COLORS = ["#35D0BA", "#FFB86B", "#C792EA", "#FF7AA2", "#70B7FF", "#FFD166"]
KOSIS_VEHICLE_TYPES = {"승용", "승합", "화물", "특수"}

st.set_page_config(page_title="CAR DATA / INSIGHTS", page_icon="🚗", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
:root{--bg:#07090d;--card:#111923;--line:#2a3948;--text:#f5f7fa;--muted:#9aabbc;--mint:#35d0ba}
.stApp{background:var(--bg);color:var(--text)} .block-container{max-width:1380px;padding-top:1.4rem;padding-bottom:3rem}
h1,h2,h3,h4,p,label,[data-testid="stMarkdownContainer"]{color:var(--text)}
[data-testid="stSidebar"]{background:#0d1118;border-right:1px solid var(--line)} [data-testid="stSidebar"] *{color:var(--text)}
[data-testid="stSidebarCollapseButton"],[data-testid="stSidebarCollapsedControl"]{display:none!important}
[data-testid="stHeader"],[data-testid="stToolbar"]{background:var(--bg)!important;border-bottom:0!important}
[data-testid="stHeader"]{border-bottom:0!important}
[data-testid="stTabs"] button[role="tab"]{color:var(--muted);font-weight:700}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"]{color:var(--mint)!important;border-bottom-color:var(--mint)!important}
.kicker{font-size:.75rem;letter-spacing:.18em;color:var(--mint);font-weight:800}.page-intro{padding:5px 2px 18px}
.page-intro h1{font-size:2.25rem;margin:.35rem 0}.muted{color:var(--muted)}
.faq-hero{margin:0 0 1.45rem;padding:2rem 2.2rem;border:1px solid var(--line);border-radius:24px;background:#0d141d}
.faq-hero h1{font-size:2.25rem;margin:.35rem 0 1rem}.faq-hero .muted{margin:0;font-size:1.05rem}
[data-testid="stMetric"]{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:15px}
[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--line)!important;border-radius:16px!important;background:var(--card)}
.stButton>button,.stDownloadButton>button{border:1px solid #33475a;border-radius:11px;background:#151e29;color:var(--text);font-weight:700}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--mint);color:var(--mint)}
.stButton>button[kind="primary"]{border-color:var(--mint);color:var(--mint);background:#122b2b}
div[data-testid="stSegmentedControl"],div[data-testid="stButtonGroup"]{margin:.2rem 0 .8rem}
div[data-testid="stSegmentedControl"] label p,div[data-testid="stButtonGroup"] label p{color:var(--muted)!important;font-size:.84rem;font-weight:800;letter-spacing:.04em}
div[data-testid="stSegmentedControl"] button,div[data-testid="stButtonGroup"] button,[data-baseweb="button-group"] button{min-height:42px!important;border:1px solid #33475a!important;border-radius:10px!important;background:#151e29!important;color:var(--text)!important;font-weight:700!important;transition:all .18s ease}
div[data-testid="stSegmentedControl"] button *,div[data-testid="stButtonGroup"] button *{color:inherit!important}
div[data-testid="stSegmentedControl"] button:hover,div[data-testid="stButtonGroup"] button:hover,[data-baseweb="button-group"] button:hover{border-color:var(--mint)!important;background:#151e29!important;color:var(--mint)!important}
div[data-testid="stSegmentedControl"] button[aria-pressed="true"],div[data-testid="stButtonGroup"] button[aria-pressed="true"],[data-baseweb="button-group"] button[aria-pressed="true"],div[data-testid="stSegmentedControl"] button[aria-checked="true"],div[data-testid="stButtonGroup"] button[aria-checked="true"],[data-baseweb="button-group"] button[aria-checked="true"],div[data-testid="stSegmentedControl"] button[data-selected="true"],div[data-testid="stButtonGroup"] button[data-selected="true"]{border-color:var(--mint)!important;background:#0d3a37!important;color:var(--mint)!important;box-shadow:0 0 0 1px rgba(53,208,186,.2),0 7px 18px rgba(0,0,0,.24)}
div[data-testid="stExpander"]{margin-bottom:.7rem;overflow:hidden;border:1px solid var(--line)!important;border-radius:14px!important;background:var(--card);box-shadow:0 5px 16px rgba(0,0,0,.16)}
div[data-testid="stExpander"] details{border:0!important;background:var(--card)!important}
div[data-testid="stExpander"] summary,div[data-testid="stExpander"] details>summary{padding:.18rem .35rem!important;background:var(--card)!important;color:var(--text)!important;font-size:1rem!important;font-weight:700!important}
div[data-testid="stExpander"] summary *,div[data-testid="stExpander"] details>summary *{color:var(--text)!important}
div[data-testid="stExpander"] summary:hover,div[data-testid="stExpander"] details>summary:hover{background:#151e29!important}
div[data-testid="stExpander"] [data-testid="stExpanderDetails"]{border-top:1px solid var(--line);background:#0d141d;padding-top:1rem}
.faq-answer-label{margin-bottom:.25rem;color:var(--mint);font-size:.82rem;font-weight:800;letter-spacing:.08em}
div[role="radiogroup"]{gap:.25rem} div[role="radiogroup"] label{margin-right:.2rem}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--card)}
[data-testid="stDataFrame"] [role="grid"],[data-testid="stDataFrame"] canvas{background:var(--card)!important}
.legend-row{display:flex;justify-content:center;gap:18px;flex-wrap:wrap;color:var(--muted);font-size:.86rem;margin:.2rem 0 .7rem}
.legend-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
.value-bars{display:grid;gap:1rem;padding:.25rem 0}.value-bar-row{display:grid;grid-template-columns:minmax(130px,23%) minmax(120px,1fr) max-content;gap:1rem;align-items:center}.value-bar-label{color:var(--muted);font-size:.94rem;font-weight:650}.value-bar-track{height:18px;background:#202c38;border-radius:999px;overflow:hidden}.value-bar-fill{height:100%;min-width:2px;border-radius:999px;box-shadow:0 5px 14px rgba(0,0,0,.18)}.value-bar-number{min-width:110px;text-align:right;color:var(--text);font-size:.95rem;font-weight:750}@media(max-width:700px){.value-bar-row{grid-template-columns:1fr max-content;gap:.45rem}.value-bar-track{grid-column:1 / -1;grid-row:2}.value-bar-number{min-width:0}.value-bar-label{font-size:.86rem}}
.criteria{display:flex;gap:13px;align-items:center;margin:.45rem 0 1rem;color:var(--muted)}.criteria strong{font-size:1.08rem;color:var(--text)}
.filter-title{font-size:.87rem;color:var(--muted);padding-top:.35rem}
@media(max-width:800px){.block-container{padding-left:1rem;padding-right:1rem}}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300, show_spinner="연료별·성별 파일 자료를 불러오는 중입니다.")
def load_file_data() -> tuple[pd.DataFrame, str]:
    try:
        port = int(str(ENV.get("MYSQL_PORT") or "3306").strip())
        connection = pymysql.connect(
            host=str(ENV.get("MYSQL_HOST") or "127.0.0.1"), port=port,
            user=str(ENV.get("MYSQL_USER") or "root"), password=str(ENV.get("MYSQL_PASSWORD") or ""),
            database=str(ENV.get("MYSQL_DATABASE") or "vehicle_db"), charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor, connect_timeout=8, read_timeout=90, autocommit=True)
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""SELECT period,data_type,sido,sigungu,usage_type,fuel,gender,
                    age_group,size_group,registration_count FROM {TABLE}
                    WHERE period REGEXP '^[0-9]{{4}}-[0-9]{{2}}$' ORDER BY period,sido,sigungu""")
                frame = pd.DataFrame(cursor.fetchall())
        finally:
            connection.close()
        if not frame.empty:
            return prepare(frame), "MySQL"
    except Exception:
        pass
    for path in CSV_CANDIDATES:
        if path.exists():
            frame = pd.read_csv(path, encoding="utf-8-sig").rename(columns={
                "기준년월":"period", "시도":"sido", "시군구":"sigungu", "용도":"usage_type",
                "연료":"fuel", "성별":"gender", "연령대":"age_group", "규모":"size_group", "등록대수":"registration_count"})
            return prepare(frame), f"CSV · {path.name}"
    return pd.DataFrame(), "자료 없음"


@st.cache_data(ttl=60 * 60, show_spinner="KOSIS 지역별·차종별 자료를 불러오는 중입니다.")
def load_kosis_region_usage_data(periods: tuple[str, ...]) -> tuple[pd.DataFrame, str]:
    """선택한 기준년월을 KOSIS에 각각 요청해 지역별·차종별 탭 형식으로 바꾼다."""
    try:
        api_key = st.secrets.get("KOSIS_API_KEY") or ENV.get("KOSIS_API_KEY")
    except Exception:
        api_key = ENV.get("KOSIS_API_KEY")
    if not api_key:
        return pd.DataFrame(), "KOSIS API 키 없음"

    rows = []
    requested_periods = tuple(sorted({period for period in periods if len(period) == 6 and period.isdigit()}))
    if not requested_periods:
        return pd.DataFrame(), "KOSIS 조회를 위한 기준년월을 선택해 주세요"

    for year_month in requested_periods:
        params = {
            "method": "getList", "apiKey": api_key,
            "itmId": "13103873443T1+13103873443T2+13103873443T3+13103873443T4+",
            "objL1": "ALL", "objL2": "13102873443B.0001+", "objL3": "ALL",
            "format": "json", "jsonVD": "Y", "prdSe": "M",
            "startPrdDe": year_month, "endPrdDe": year_month,
            "orgId": "116", "tblId": "DT_MLTM_5498",
        }
        try:
            response = requests.get("https://kosis.kr/openapi/Param/statisticsParameterData.do", params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except Exception as error:
            return pd.DataFrame(), f"KOSIS API 요청 실패 ({year_month}): {error}"
        if not isinstance(payload, list):
            return pd.DataFrame(), f"KOSIS API 응답 형식 오류 ({year_month})"

        for item in payload:
            # registration.py와 동일하게 차종별 합계 항목만 사용한다.
            # 이 조건이 없으면 같은 차종의 세부 항목까지 함께 더해져 4배로 집계된다.
            if str(item.get("ITM_NM") or "").strip() != "계":
                continue
            period = str(item.get("PRD_DE") or "")
            vehicle_type = str(item.get("C3_NM") or "").strip()
            sido = str(item.get("C1_NM") or "").strip()
            if vehicle_type not in KOSIS_VEHICLE_TYPES:
                continue
            try:
                count = int(str(item.get("DT") or "0").replace(",", ""))
            except ValueError:
                continue
            if len(period) < 6 or not vehicle_type or not sido:
                continue
            rows.append({"period": f"{period[:4]}-{period[4:6]}", "sido": sido, "sigungu": "전체",
                         "usage_type": vehicle_type, "fuel": "전체", "gender": "전체",
                         "age_group": "전체", "size_group": "전체", "registration_count": count})
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail, "KOSIS API 응답 데이터 없음"
    total = detail.groupby(["period", "sido"], as_index=False)["registration_count"].sum()
    total = total.assign(sigungu="전체", usage_type="전체", fuel="전체", gender="전체", age_group="전체", size_group="전체")
    return prepare(pd.concat([detail, total], ignore_index=True)), "KOSIS API"


@st.cache_data(ttl=300, show_spinner="FAQ 자료를 불러오는 중입니다.")
def load_faq_data() -> tuple[pd.DataFrame, str]:
    """MySQL FAQ 테이블을 우선 조회하고, 연결이 안 되면 원본 CSV를 사용한다."""
    columns = ["company", "category_main", "category_sub", "question", "answer"]
    try:
        port = int(str(ENV.get("MYSQL_PORT") or "3306").strip())
        connection = pymysql.connect(
            host=str(ENV.get("MYSQL_HOST") or "127.0.0.1"), port=port,
            user=str(ENV.get("MYSQL_USER") or "root"), password=str(ENV.get("MYSQL_PASSWORD") or ""),
            database=str(ENV.get("MYSQL_DATABASE") or "vehicle_db"), charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor, connect_timeout=8, read_timeout=30, autocommit=True)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT company, category_main, category_sub, question, answer "
                    f"FROM {FAQ_TABLE} ORDER BY company, category_main, category_sub, question"
                )
                faq = pd.DataFrame(cursor.fetchall())
        finally:
            connection.close()
        if not faq.empty:
            return faq.reindex(columns=columns).fillna(""), "MySQL"
    except Exception:
        pass

    if FAQ_CSV.exists():
        faq = pd.read_csv(FAQ_CSV, encoding="utf-8-sig")
        return faq.reindex(columns=columns).fillna(""), f"CSV · {FAQ_CSV.name}"
    return pd.DataFrame(columns=columns), "자료 없음"


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    defaults = {"period":"", "sido":"전체", "sigungu":"전체", "usage_type":"전체", "fuel":"전체",
                "gender":"전체", "age_group":"전체", "size_group":"전체"}
    for column, default in defaults.items():
        if column not in result:
            result[column] = default
        result[column] = result[column].fillna(default).astype(str).str.strip().replace("", default)
    result["period"] = result["period"].str[:7]
    result["registration_count"] = pd.to_numeric(result["registration_count"], errors="coerce").fillna(0).astype("int64")
    result["age_group"] = result["age_group"].replace({"10대이하":"10대 이하", "90대이상":"90대 이상", "합":"계"})
    result = result[~result["sido"].isin(["계", "총계", "합계"])].copy()
    result["year"], result["month"] = result["period"].str[:4], result["period"].str[5:7]
    return result


def overall_rows(frame):
    return frame[frame[["sigungu","usage_type","fuel","gender","age_group","size_group"]].eq("전체").all(axis=1)]


def region_rows(frame):
    return frame[frame[["usage_type","fuel","gender","age_group","size_group"]].eq("전체").all(axis=1)]


def usage_rows(frame):
    return frame[(frame["usage_type"] != "전체") & frame[["sigungu","fuel","gender","age_group","size_group"]].eq("전체").all(axis=1)]


def fuel_rows(frame):
    return frame[(frame["fuel"] != "전체") & frame[["sigungu","usage_type","gender","age_group","size_group"]].eq("전체").all(axis=1)]


def gender_rows(frame):
    return frame[(frame["gender"] != "전체") & frame[["sigungu","usage_type","fuel","size_group"]].eq("전체").all(axis=1)]


def set_page(page: str, tab: str | None = None):
    """사이드바와 홈 카드에서 최상위 화면만 이동한다.

    tab 인수는 이전 코드와의 호환을 위해 남겨 두지만, 본문 탭 선택은 st.tabs가 담당한다.
    """
    st.session_state.page = page


def init_state(frame: pd.DataFrame):
    latest = sorted(frame["period"].unique())[-1]
    defaults = {"page":"home", "car_tab":"통합", "faq_tab":"통합", "selected_years":[latest[:4]],
                "selected_months":[latest[5:7]], "shared_sido":"전체", "region_sigungu":"전체",
                "usage_choice":"전체", "fuel_choice":"전체", "gender_choice":"전체", "age_choice":"전체"}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if "pending_sido" in st.session_state:
        st.session_state.shared_sido = st.session_state.pop("pending_sido")


def sync_date_widget_keys(kind: str, values: list[str]):
    selected = st.session_state[f"selected_{kind}"]
    st.session_state[f"{kind}_all"] = "전체" in selected
    for value in values:
        st.session_state[f"{kind}_{value}"] = value in selected


def date_all_changed(kind: str, values: list[str]):
    st.session_state[f"selected_{kind}"] = ["전체"] if st.session_state[f"{kind}_all"] else []
    sync_date_widget_keys(kind, values)


def date_item_changed(kind: str, value: str, values: list[str]):
    selected = [item for item in st.session_state[f"selected_{kind}"] if item != "전체"]
    checked = st.session_state[f"{kind}_{value}"]
    if checked and value not in selected:
        limit = 2 if kind == "years" else (1 if len([y for y in st.session_state.selected_years if y != "전체"]) == 2 else 2)
        if len(selected) < limit:
            selected.append(value)
    elif not checked:
        selected = [item for item in selected if item != value]
    st.session_state[f"selected_{kind}"] = selected or ["전체"]
    if kind == "years" and len(selected) == 2:
        months = [m for m in st.session_state.selected_months if m != "전체"]
        if len(months) > 1:
            st.session_state.selected_months = months[:1]
            sync_date_widget_keys("months", [f"{m:02d}" for m in range(1, 13)])
    sync_date_widget_keys(kind, values)


def checkbox_row(label: str, values: list[str], kind: str):
    selected = st.session_state[f"selected_{kind}"]
    max_count = 2 if kind == "years" else (1 if len([y for y in st.session_state.selected_years if y != "전체"]) == 2 else 2)
    with st.container(border=True):
        title_col, all_col = st.columns([1, 12])
        title_col.markdown(f'<div class="filter-title">{label}</div>', unsafe_allow_html=True)
        all_col.checkbox("전체", key=f"{kind}_all", on_change=date_all_changed, args=(kind, values))
        item_columns = st.columns(min(len(values), 12))
        active = [v for v in selected if v != "전체"]
        for index, value in enumerate(values):
            disabled = "전체" in selected or (len(active) >= max_count and value not in active)
            item_columns[index % len(item_columns)].checkbox(value, key=f"{kind}_{value}", disabled=disabled,
                on_change=date_item_changed, args=(kind, value, values))


def common_filters(frame: pd.DataFrame, years: list[str] | None = None, months: list[str] | None = None):
    years = years or sorted(frame["year"].dropna().unique())
    months = months or [f"{month:02d}" for month in range(1, 13)]
    if "years_all" not in st.session_state:
        sync_date_widget_keys("years", years)
    if "months_all" not in st.session_state:
        sync_date_widget_keys("months", months)
    checkbox_row("년", years, "years")
    checkbox_row("월", months, "months")
    sidos = ["전체"] + sorted(overall_rows(frame)["sido"].unique())
    st.radio("시도", sidos, horizontal=True, key="shared_sido")
    if st.session_state.shared_sido == "전체":
        st.session_state.region_sigungu = "전체"


def selected_kosis_periods() -> tuple[str, ...]:
    """비교 필터에서 선택한 최대 두 개의 월을 KOSIS 요청 단위로 만든다."""
    years = [year for year in st.session_state.selected_years if year != "전체"]
    months = [month for month in st.session_state.selected_months if month != "전체"]
    return tuple(f"{year}{month}" for year in years for month in months)


def kosis_filter_options() -> tuple[list[str], list[str]]:
    """registration.py와 같은 단일 월 조회 범위를 비교 필터에 제공한다."""
    latest = date.today().replace(day=1) - timedelta(days=1)
    years = [str(year) for year in range(2016, latest.year + 1)]
    selected_years = [year for year in st.session_state.selected_years if year != "전체"]
    max_month = latest.month if str(latest.year) in selected_years else 12
    months = [f"{month:02d}" for month in range(1, max_month + 1)]
    return years, months


def filter_common(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame
    if "전체" not in st.session_state.selected_years:
        result = result[result["year"].isin(st.session_state.selected_years)]
    if "전체" not in st.session_state.selected_months:
        result = result[result["month"].isin(st.session_state.selected_months)]
    if st.session_state.shared_sido != "전체":
        result = result[result["sido"] == st.session_state.shared_sido]
    return result


def period_label() -> str:
    years, months = st.session_state.selected_years, st.session_state.selected_months
    year_text = "전체" if "전체" in years else ", ".join(years)
    month_text = "전체" if "전체" in months else ", ".join(f"{m}월" for m in months)
    return "전체" if year_text == month_text == "전체" else f"{year_text}년 / {month_text}"


def latest_snapshot(frame: pd.DataFrame) -> pd.DataFrame:
    return frame if frame.empty else frame[frame["period"] == frame["period"].max()]


def comparison_frames(frame: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    years = [y for y in st.session_state.selected_years if y != "전체"]
    months = [m for m in st.session_state.selected_months if m != "전체"]
    result = []
    if len(years) == 2:
        for year in years:
            subset = frame[frame["year"] == year]
            if len(months) == 1:
                subset = subset[subset["month"] == months[0]]
            subset = latest_snapshot(subset)
            if not subset.empty:
                result.append((subset["period"].max(), subset))
    elif len(months) == 2:
        for month in months:
            subset = frame[frame["month"] == month]
            if len(years) == 1:
                subset = subset[subset["year"] == years[0]]
            subset = latest_snapshot(subset)
            if not subset.empty:
                result.append((subset["period"].max(), subset))
    return result if len(result) == 2 else []


def chart_style(figure, height=390):
    figure.update_layout(template="plotly_dark", paper_bgcolor="#111923", plot_bgcolor="#111923",
        font_color="#dce5ee", height=height, margin=dict(l=15,r=25,t=35,b=35), xaxis_title=None, yaxis_title=None)
    return figure


def bar_chart(data: pd.DataFrame, name: str, value: str, color="#35D0BA", horizontal=True, key: str | None = None):
    """목업과 같은 정렬형 막대 목록으로 등록대수 비교를 표시한다."""
    if data.empty:
        st.info("선택한 조건의 자료가 없습니다.")
        return
    ordered = data.copy()
    ordered[value] = pd.to_numeric(ordered[value], errors="coerce").fillna(0)
    ordered = ordered.sort_values(value, ascending=False)
    maximum = max(float(ordered[value].max()), 1.0)
    rows = "".join(
        f'<div class="value-bar-row"><div class="value-bar-label">{escape(str(row[name]))}</div>'
        f'<div class="value-bar-track"><div class="value-bar-fill" style="width:{float(row[value]) / maximum * 100:.2f}%;background:{color}"></div></div>'
        f'<div class="value-bar-number">{int(row[value]):,}대</div></div>'
        for _, row in ordered.iterrows()
    )
    st.markdown(f'<div class="value-bars">{rows}</div>', unsafe_allow_html=True)


def trend_chart(frame: pd.DataFrame, color="#35D0BA", key: str | None = None):
    """월별 등록대수를 누적하지 않는 일반 선그래프로 표시한다."""
    trend = frame.groupby("period", as_index=False)["registration_count"].sum().sort_values("period")
    if trend.empty:
        st.info("선택한 조건의 자료가 없습니다.")
        return
    figure = px.line(trend, x="period", y="registration_count", markers=True, text="registration_count")
    figure.update_traces(line_color=color, line_width=3, marker_size=7,
        texttemplate="%{text:,.0f}", textposition="top center")
    st.plotly_chart(chart_style(figure), width="stretch", key=key)


def grouped(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    return frame.groupby(column, as_index=False)["registration_count"].sum().sort_values("registration_count", ascending=False)


def category_colors(names: list[str]) -> dict[str, str]:
    return {name: COLORS[index % len(COLORS)] for index, name in enumerate(names)}


def donut(values: pd.DataFrame, category: str, center: str, color_map: dict[str, str]):
    figure = go.Figure(go.Pie(labels=values[category], values=values["registration_count"], hole=.62,
        marker_colors=[color_map.get(value, COLORS[0]) for value in values[category]],
        textinfo="percent", textfont=dict(color="#9aabbc", size=12), sort=False, showlegend=False))
    figure.add_annotation(text=center, x=.5, y=.5, showarrow=False, font=dict(color="#f5f7fa", size=14))
    chart_style(figure, 315)
    figure.update_layout(margin=dict(l=5,r=5,t=5,b=5), showlegend=False)
    return figure


def shared_legend(names: list[str], color_map: dict[str, str]):
    items = "".join(f'<span><i class="legend-dot" style="background:{color_map[name]}"></i>{name}</span>' for name in names)
    st.markdown(f'<div class="legend-row">{items}</div>', unsafe_allow_html=True)


def top_categories(frame: pd.DataFrame, category: str) -> pd.DataFrame:
    values = grouped(frame, category)
    if len(values) <= 5:
        return values
    top = values.head(4).copy()
    other = pd.DataFrame([{category:"기타", "registration_count":values.iloc[4:]["registration_count"].sum()}])
    return pd.concat([top, other], ignore_index=True)


def comparison_panel(frame: pd.DataFrame, category: str, title: str, color="#35D0BA"):
    comparisons = comparison_frames(frame)
    if not comparisons:
        return False
    with st.container(border=True):
        st.subheader(f"{title} 등록대수 비교")
        columns = st.columns(2)
        data, all_names = [], []
        for label, subset in comparisons:
            values = top_categories(subset, category)
            data.append((label, values)); all_names.extend(values[category].tolist())
        color_map = category_colors(list(dict.fromkeys(all_names)))
        for column, (label, values) in zip(columns, data):
            with column:
                st.markdown(f"**{label}**"); bar_chart(values, category, "registration_count", color,
                    key=f"comparison-bar-{title}-{category}-{label}")
        st.divider(); st.subheader(f"{title} 구성비 비교")
        donut_columns = st.columns(2)
        for column, (label, values) in zip(donut_columns, data):
            with column:
                st.plotly_chart(donut(values, category, label, color_map), width="stretch",
                    key=f"comparison-donut-{title}-{category}-{label}")
        shared_legend(list(dict.fromkeys(all_names)), color_map)
    return True


def data_table(frame: pd.DataFrame, columns: list[str], filename: str):
    labels = {"period":"기준년월", "sido":"시도", "sigungu":"시군구", "usage_type":"용도", "fuel":"연료",
              "gender":"성별", "age_group":"연령대", "size_group":"규모", "registration_count":"등록대수"}
    display = frame[columns].copy().rename(columns=labels)
    if "등록대수" in display:
        display = display[[column for column in display.columns if column != "등록대수"] + ["등록대수"]]
    styled_display = display.style.set_properties(**{"background-color":"#111923", "color":"#f5f7fa"}).set_table_styles([
        {"selector":"th", "props":[("background-color", "#151e29"), ("color", "#f5f7fa")]},
    ])
    with st.container(border=True):
        st.subheader("데이터 표")
        st.dataframe(styled_display, hide_index=True, width="stretch", height=390)
        st.download_button("결과 데이터 다운로드", display.to_csv(index=False).encode("utf-8-sig"),
            file_name=filename, mime="text/csv", key=f"download_{filename}")


def inline_selectbox(label: str, options: list[str], key: str, disabled: bool = False):
    """선택 항목의 제목과 드롭다운을 같은 줄에 배치한다."""
    label_column, input_column, _ = st.columns([1.3, 2.2, 6.5], vertical_alignment="center")
    with label_column:
        st.markdown(f'<div class="filter-title">{label}</div>', unsafe_allow_html=True)
    with input_column:
        return st.selectbox(label, options, key=key, disabled=disabled, label_visibility="collapsed")


def canonical_sigungu(name: str) -> str:
    value = str(name).strip()
    return value[:-1] if " " not in value and len(value) >= 2 and value[-1] in "시군구" else value


def normalized_districts(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame[frame["sigungu"] != "전체"].copy()
    result["sigungu"] = result["sigungu"].map(canonical_sigungu)
    return result.groupby(["period","year","month","sido","sigungu"], as_index=False)["registration_count"].max()


def integrated_page(frame: pd.DataFrame):
    source = filter_common(overall_rows(frame))
    st.markdown(f'<div class="criteria"><span>기준년월</span><strong>{period_label()}</strong></div>', unsafe_allow_html=True)
    comparisons = comparison_frames(source)
    area = "전국" if st.session_state.shared_sido == "전체" else st.session_state.shared_sido
    if comparisons:
        with st.container(border=True):
            st.subheader("등록대수")
            total_rows = pd.DataFrame([{"구분":f"{area} ({label})", "등록대수":subset["registration_count"].sum()} for label, subset in comparisons])
            bar_chart(total_rows, "구분", "등록대수", key="integrated-comparison-bar")
        with st.container(border=True):
            st.subheader(f"{area} 등록대수 비교")
            cols = st.columns(2)
            for col, (label, subset) in zip(cols, comparisons):
                col.metric(label, f"{subset['registration_count'].sum():,.0f}대")
        composition = filter_common(normalized_districts(region_rows(frame)))
        category = "sido" if st.session_state.shared_sido == "전체" else "sigungu"
        donut_data, names = [], []
        for label, _ in comparisons:
            values = top_categories(composition[composition["period"] == label], category)
            donut_data.append((label, values)); names.extend(values[category].tolist())
        color_map = category_colors(list(dict.fromkeys(names)))
        with st.container(border=True):
            st.subheader(f"{area} {'시도' if category == 'sido' else '시군구'} 구성비")
            cols = st.columns(2)
            for col, (label, values) in zip(cols, donut_data):
                with col: st.plotly_chart(donut(values, category, label, color_map), width="stretch",
                    key=f"integrated-comparison-donut-{label}")
            shared_legend(list(dict.fromkeys(names)), color_map)
    else:
        snapshot = latest_snapshot(source)
        with st.container(border=True):
            st.subheader("등록대수"); trend_chart(source, key="integrated-trend")
        composition = latest_snapshot(filter_common(normalized_districts(region_rows(frame))))
        category = "sido" if st.session_state.shared_sido == "전체" else "sigungu"
        values = top_categories(composition, category); color_map = category_colors(values[category].tolist())
        with st.container(border=True):
            st.subheader(f"{area} {'시도' if category == 'sido' else '시군구'} 구성비")
            center = snapshot["period"].max() if not snapshot.empty else period_label()
            st.plotly_chart(donut(values, category, center, color_map), width="stretch", key="integrated-donut")
            shared_legend(values[category].tolist(), color_map)
    data_table(source, ["period","sido","sigungu","registration_count"], "자동차_등록현황_통합.csv")


def region_page(frame: pd.DataFrame):
    districts = normalized_districts(region_rows(frame))
    has_district_data = not districts.empty
    options = ["전체"] if st.session_state.shared_sido == "전체" else ["전체"] + sorted(districts.loc[districts["sido"]==st.session_state.shared_sido,"sigungu"].unique())
    if st.session_state.region_sigungu not in options:
        st.session_state.region_sigungu = "전체"
    inline_selectbox("시군구", options, "region_sigungu", disabled=st.session_state.shared_sido=="전체" or not has_district_data)
    if not has_district_data:
        st.caption("KOSIS 지역별 자료는 시도 단위로 제공되어 시군구 선택은 사용할 수 없습니다.")
    source = filter_common(districts if has_district_data else overall_rows(frame))
    if st.session_state.region_sigungu != "전체": source = source[source["sigungu"]==st.session_state.region_sigungu]
    totals = grouped(latest_snapshot(filter_common(overall_rows(frame))),"sido")
    area = st.session_state.region_sigungu if st.session_state.region_sigungu!="전체" else (st.session_state.shared_sido if st.session_state.shared_sido!="전체" else "전국")
    comparisons = comparison_frames(source)
    with st.container(border=True):
        st.subheader(f"{area} 등록대수")
        if comparisons:
            values = pd.DataFrame([{"기준년월":label,"등록대수":subset["registration_count"].sum()} for label,subset in comparisons])
            bar_chart(values,"기준년월","등록대수","#FFB86B", key="region-comparison-bar")
        elif st.session_state.shared_sido == "전체": bar_chart(totals,"sido","registration_count","#FFB86B", key="region-sido-bar")
        else: trend_chart(source,"#FFB86B", key="region-trend")
    data_table(source,["period","sido","sigungu","registration_count"],"자동차_지역별_조회결과.csv")


def category_page(frame: pd.DataFrame, source_func, category: str, title: str, state_key: str, color: str):
    data = filter_common(source_func(frame)); options = ["전체"] + sorted(data[category].dropna().unique())
    if st.session_state[state_key] not in options: st.session_state[state_key] = "전체"
    inline_selectbox(title.replace("별","")+" 선택", options, state_key)
    if st.session_state[state_key] != "전체": data = data[data[category]==st.session_state[state_key]]
    if not comparison_panel(data,category,title,color):
        snapshot = latest_snapshot(data); values = grouped(snapshot,category); left,right = st.columns([1.25,.75])
        with left:
            with st.container(border=True): st.subheader(f"{title} 등록대수"); bar_chart(values,category,"registration_count",color,key=f"{title}-bar")
        with right:
            with st.container(border=True):
                st.subheader("구성비"); parts = top_categories(snapshot,category); color_map = category_colors(parts[category].tolist())
                center = snapshot["period"].max() if not snapshot.empty else period_label()
                st.plotly_chart(donut(parts,category,center,color_map),width="stretch",key=f"{title}-donut"); shared_legend(parts[category].tolist(),color_map)
    data_table(data,["period","sido",category,"registration_count"],f"자동차_{title}_조회결과.csv")


def gender_page(frame: pd.DataFrame):
    data = filter_common(gender_rows(frame)); genders = ["전체"] + sorted(data["gender"].unique())
    if st.session_state.gender_choice not in genders: st.session_state.gender_choice = "전체"
    left,right = st.columns(2)
    with left: inline_selectbox("성별 선택", genders, "gender_choice")
    gender = st.session_state.gender_choice
    if gender != "전체": data = data[data["gender"]==gender]
    if gender == "기타": ages=["법인 및 사업자"]
    else: ages=["전체"]+sorted(age for age in data["age_group"].unique() if age not in ["전체","계","법인 및 사업자"])
    if st.session_state.age_choice not in ages: st.session_state.age_choice = ages[0]
    with right: inline_selectbox("연령대 선택", ages, "age_choice", disabled=gender=="기타")
    if st.session_state.age_choice != "전체": data = data[data["age_group"]==st.session_state.age_choice]
    else: data = data[~data["age_group"].isin(["전체","계"])]
    if not comparison_panel(data,"age_group","성별·연령별","#FF7AA2"):
        snapshot=latest_snapshot(data); values=grouped(snapshot,"age_group"); left,right=st.columns([1.25,.75])
        with left:
            with st.container(border=True): st.subheader("성별·연령별 등록대수"); bar_chart(values,"age_group","registration_count","#FF7AA2",key="gender-bar")
        with right:
            with st.container(border=True):
                st.subheader("연령대 구성비"); parts=top_categories(snapshot,"age_group"); color_map=category_colors(parts["age_group"].tolist())
                center=snapshot["period"].max() if not snapshot.empty else period_label()
                st.plotly_chart(donut(parts,"age_group",center,color_map),width="stretch",key="gender-donut"); shared_legend(parts["age_group"].tolist(),color_map)
    data_table(data,["period","sido","gender","age_group","registration_count"],"자동차_성별_연령별_조회결과.csv")


def faq_segmented_filter(label: str, options: list[str], key: str) -> str:
    """동적으로 바뀌는 FAQ 옵션에서도 유효한 버튼 선택을 유지한다."""
    if st.session_state.get(key) not in options:
        st.session_state[key] = "전체"
    return st.segmented_control(label, options, key=key) or "전체"


def faq_results(faq: pd.DataFrame, company: str | None, key_prefix: str):
    """기업·대분류·검색어 조건으로 FAQ를 좁혀 펼침 카드로 표시한다."""
    view = faq.copy() if company is None else faq[faq["company"] == company].copy()

    main_options = ["전체"] + sorted(value for value in view["category_main"].dropna().unique() if value)
    main = faq_segmented_filter("1. 대분류", main_options, f"{key_prefix}_main")
    if main != "전체":
        view = view[view["category_main"] == main]

    keyword = st.text_input("FAQ 검색", placeholder="질문 또는 답변을 입력하세요", key=f"{key_prefix}_keyword")
    if keyword.strip():
        query = keyword.strip()
        mask = view["question"].str.contains(query, case=False, regex=False, na=False)
        mask |= view["answer"].str.contains(query, case=False, regex=False, na=False)
        view = view[mask]

    st.caption(f"검색 결과 {len(view):,}건")
    if view.empty:
        st.info("선택한 조건의 FAQ가 없습니다.")
        return

    for _, row in view.iterrows():
        category = " / ".join(part for part in [row["category_main"], row["category_sub"]] if part)
        with st.expander(f"Q. {row['question']}"):
            details = " · ".join(part for part in [row["company"], category] if part)
            if details:
                st.caption(details)
            st.markdown('<div class="faq-answer-label">ANSWER</div>', unsafe_allow_html=True)
            st.write(row["answer"])


def faq_page(faq: pd.DataFrame, faq_source: str):
    """참고 FAQ의 버튼식 필터와 펼침식 답변을 현재 테마로 표시한다."""
    st.markdown(
        '<div class="faq-hero"><div class="kicker">CUSTOMER SUPPORT</div>'
        '<h1>FAQ</h1><p class="muted">자동차 제조사별 자주 묻는 질문과 답변을 확인합니다.</p></div>',
        unsafe_allow_html=True,
    )
    company_key = "faq_company"
    if st.session_state.get(company_key) not in FAQ_TABS:
        st.session_state[company_key] = "통합"
    selected_company = st.segmented_control("제조사", FAQ_TABS, key=company_key) or "통합"
    company = None if selected_company == "통합" else selected_company
    faq_results(faq, company, f"faq_{selected_company}")


def home_page():
    st.markdown('<div class="page-intro"><h1>INSIGHTS <span class="kicker">CAR DATA</span></h1><p class="muted">자동차 통계를 원하는 기준으로 살펴보고, FAQ에서 자주 묻는 질문도 확인할 수 있습니다.</p></div>',unsafe_allow_html=True)
    left,right=st.columns(2)
    with left: st.button("자동차 등록현황\n\n지역·시군구와 용도·연료·성별·연령대를 선택해 실제 자료를 확인합니다.",key="home_car",on_click=set_page,args=("car","통합"),width="stretch")
    with right: st.button("FAQ\n\n자주 확인하는 질문을 모아둔 화면입니다.",key="home_faq",on_click=set_page,args=("faq","통합"),width="stretch")


def sidebar():
    st.sidebar.markdown('<div class="kicker">CAR DATA</div><h2>INSIGHTS</h2>',unsafe_allow_html=True)
    car_active,faq_active=st.session_state.page=="car",st.session_state.page=="faq"
    st.sidebar.button("자동차 등록 현황",key="nav_car",type="primary" if car_active else "secondary",on_click=set_page,args=("car","통합"),width="stretch")
    st.sidebar.button("FAQ",key="nav_faq",type="primary" if faq_active else "secondary",on_click=set_page,args=("faq","통합"),width="stretch")


def car_page(file_frame: pd.DataFrame):
    st.markdown('<div class="page-intro"><div class="kicker">REGISTRATION DASHBOARD</div><h1>자동차 등록 현황</h1></div>',unsafe_allow_html=True)
    kosis_years, kosis_months = kosis_filter_options()
    common_filters(file_frame, kosis_years, kosis_months)
    selected_periods = selected_kosis_periods()
    api_frame, api_source = load_kosis_region_usage_data(selected_periods)
    if api_frame.empty:
        api_frame = file_frame
        st.warning(f"지역별·차종별 화면은 {api_source}로 인해 임시로 파일 자료를 표시합니다.")
    else:
        selected_label = ", ".join(f"{period[:4]}년 {period[4:]}월" for period in selected_periods)
        st.caption(f"지역별·차종별: {api_source} · {selected_label}")
    tabs = st.tabs(CAR_TABS)
    with tabs[0]:
        region_page(api_frame)
    with tabs[1]:
        category_page(api_frame, usage_rows, "usage_type", "차종별", "usage_choice", "#35D0BA")
    with tabs[2]:
        category_page(file_frame, fuel_rows, "fuel", "연료별", "fuel_choice", "#C792EA")
    with tabs[3]:
        gender_page(file_frame)


def main():
    file_frame,_file_source=load_file_data()
    if file_frame.empty:
        st.error("연료별·성별 파일 자료를 찾지 못했습니다. MySQL과 CSV 파일을 확인해 주세요."); return
    faq, faq_source = load_faq_data()
    init_state(file_frame); sidebar()
    if st.session_state.page=="home": home_page()
    elif st.session_state.page=="faq": faq_page(faq, faq_source)
    else: car_page(file_frame)


if __name__=="__main__":
    main()
