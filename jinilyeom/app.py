import streamlit as st

st.set_page_config(
    page_title = "Yeom Data",
    layout = "wide",
    initial_sidebar_state = "expanded"
)

pages = {
    "": [
        st.Page(
            "pages/registration.py",
            title = "자동차 등록 현황",
            default = True
        ),
        st.Page(
            "pages/faq.py",
            title = "FAQ"
        )
    ]
}

pg = st.navigation(pages, position = "sidebar", expanded = True)
pg.run()