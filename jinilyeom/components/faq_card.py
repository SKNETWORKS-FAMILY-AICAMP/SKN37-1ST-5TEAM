import streamlit as st

def render_faq_card(row):
    with st.container(border = True):
        c1, c2 = st.columns([5, 1])

        with c1:
            st.caption(f"{row['brand']} · {row['category']}")
            st.markdown(f"**{row['question']}**")
            st.write(row["answer"])

        with c2:
            if st.button("자세히 보기", key = f"faq_{row['id']}", use_container_width = True):
                st.session_state.faq_selected_id = int(row["id"])
                st.rerun()