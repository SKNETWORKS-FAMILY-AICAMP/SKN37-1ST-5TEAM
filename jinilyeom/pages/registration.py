import requests
import pandas as pd
import streamlit as st

from datetime import datetime

st.title("자동차 등록 현황")
st.caption("국내 자동차 등록 현황을 월별·지역별로 조회합니다.")

# =========================================================
# 기본 설정
# =========================================================
VEHICLE_TYPES = ["승용", "승합", "화물", "특수"]

REGIONS = [
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
]

# =========================================================
# KOSIS API
# =========================================================
@st.cache_data(ttl = 60 * 60)
def load_registration_data(year_month: str):
    """
    KOSIS에서 특정 월의 자동차 등록 현황 조회
    year_month: YYYYMM
    """

    api_key = st.secrets["KOSIS_API_KEY"]

    # TODO: URL 교체
    # https://kosis.kr/openapi/Param/statisticsParameterData.do
    # ?method=getList
    # &apiKey=""
    # &itmId=13103873443T4+
    # &objL1=ALL
    # &objL2=13102873443B.0001+
    # &objL3=ALL
    # &objL4=&objL5=&objL6=&objL7=&objL8=
    # &format=json
    # &jsonVD=Y
    # &prdSe=M
    # &startPrdDe=202608
    # &endPrdDe=202608
    # &orgId=116
    # &tblId=DT_MLTM_5498
    base_url = (
        "https://kosis.kr/openapi/Param/statisticsParameterData.do"
        "?method=getList"
        f"&apiKey={api_key}"
        "&itmId=13103873443T1+13103873443T2+13103873443T3+13103873443T4+"
        "&objL1=ALL"
        "&objL2=13102873443B.0001+"
        "&objL3=ALL"
        "&format=json"
        "&jsonVD=Y"
        "&prdSe=M"
        f"&startPrdDe={year_month}"
        f"&endPrdDe={year_month}"
        "&orgId=116"
        "&tblId=DT_MLTM_5498"
    )

    response = requests.get(base_url, timeout = 30)
    response.raise_for_status()

    return response.json()

# =========================================================
# API 데이터 → DataFrame
# =========================================================
def convert_to_dataframe(response_dict):
    rows = []

    for item in response_dict:
        if item.get("ITM_NM") != "계":
            continue

        vehicle_type = item.get("C3_NM")
        region = item.get("C1_NM")

        if vehicle_type not in VEHICLE_TYPES:
            continue

        if not region:
            continue

        rows.append(
            {
                "지역": region,
                "차종": vehicle_type,
                "등록대수": int(item.get("DT", 0))
            }
        )

    return pd.DataFrame(rows)

# =========================================================
# 조회 조건
# =========================================================
st.subheader("조회 조건")

col1, col2, col3, col4 = st.columns(4)

current_year = datetime.now().year
current_month = datetime.now().month - 1

years = list(range(2011, current_year + 1))

with col1:
    selected_year = st.selectbox(
        "조회 연도",
        years,
        index = years.index(current_year)
    )

with col2:
    max_month = (
        current_month
        if selected_year == current_year
        else 12
    )

    months = list(range(1, max_month + 1))

    selected_month = st.selectbox(
        "조회 월",
        months,
        index = len(months) - 1,
        format_func = lambda x: f"{x:02d}월"
    )

with col3:
    selected_region = st.selectbox("지역", ["전체"] + REGIONS)

with col4:
    selected_vehicle_type = st.selectbox("차종", ["전체"] + VEHICLE_TYPES)

year_month = f"{selected_year}{selected_month:02d}"

# =========================================================
# 데이터 조회
# =========================================================
with st.spinner("자동차 등록 데이터를 조회하고 있습니다..."):
    response_dict = load_registration_data(year_month)
    df = convert_to_dataframe(response_dict)

if df.empty:
    st.warning("조회된 데이터가 없습니다.")
    st.stop()

# =========================================================
# 필터 적용
# =========================================================
filtered = df.copy()

if selected_region != "전체":
    filtered = filtered[filtered["지역"] == selected_region]

if selected_vehicle_type != "전체":
    filtered = filtered[filtered["차종"] == selected_vehicle_type]

# =========================================================
# KPI
# =========================================================
vehicle_sum = (
    filtered
        .groupby("차종")["등록대수"]
        .sum()
        .reindex(VEHICLE_TYPES)
        .fillna(0)
)

passenger_sum = int(vehicle_sum["승용"])
van_sum = int(vehicle_sum["승합"])
truck_sum = int(vehicle_sum["화물"])
special_sum = int(vehicle_sum["특수"])

total_sum = (passenger_sum + van_sum + truck_sum + special_sum)

st.divider()

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("등록 대수", f"{total_sum:,}")
c2.metric("승용", f"{passenger_sum:,}")
c3.metric("승합", f"{van_sum:,}")
c4.metric("화물", f"{truck_sum:,}")
c5.metric("특수", f"{special_sum:,}")

# =========================================================
# 지역별 등록 현황
# =========================================================
st.divider()

st.subheader(f"{selected_year}년 {selected_month:02d}월 지역별 등록 현황")

region_data = (
    filtered
        .groupby("지역")["등록대수"]
        .sum()
        .sort_values(ascending = False)
)

if region_data.empty:
    st.info("조회 조건에 해당하는 데이터가 없습니다.")
else:
    st.bar_chart(region_data, horizontal = True)

# =========================================================
# 지역 × 차종 상세 데이터
# =========================================================
st.divider()

st.subheader("지역별 상세 데이터")

detail = (
    filtered
        .pivot_table(
            index = "지역",
            columns = "차종",
            values = "등록대수",
            aggfunc = "sum",
            fill_value = 0
        )
        .reindex(columns = VEHICLE_TYPES, fill_value = 0)
)

detail["총 등록"] = detail.sum(axis = 1)
detail = (detail.sort_values("총 등록", ascending = False).reset_index())

st.dataframe(detail, use_container_width = True, hide_index = True)