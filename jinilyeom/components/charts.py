import streamlit as st

def render_registration_charts(df):
    monthly = (
        df.groupby("월")[["승용", "승합", "화물", "특수"]].sum().sort_index()
    )

    manufacturer = (
        df.groupby("제조사")[["승용", "승합", "화물", "특수"]].sum()
    )
    manufacturer["총 등록"] = manufacturer.sum(axis = 1)
    manufacturer = manufacturer[["총 등록"]].sort_values("총 등록", ascending = False)

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("월별 등록 추이")
        st.line_chart(monthly, use_container_width = True)

    with c2:
        st.subheader("제조사별 등록 현황")
        st.bar_chart(manufacturer, use_container_width = True)