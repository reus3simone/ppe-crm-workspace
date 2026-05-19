import streamlit as st
import sys
import os

st.set_page_config(
    page_title="PPE客户开发工作区",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "PPE客户开发管理系统 v4.0"
    }
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
css_path = os.path.join(BASE_DIR, "assets", "styles.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

sys.path.append(BASE_DIR)

from pages.home import render_home_page
from pages.workspace import render_workspace
from pages.settings import render_settings

st.markdown("""
<style>
    [data-testid="stSidebarNav"] { display: none; }
</style>
""", unsafe_allow_html=True)

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "首页"

with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:8px 0 16px 0;">
        <span style="font-size:28px;">📊</span>
        <span style="font-size:18px;font-weight:700;color:#0f172a;">PPE客户开发</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    nav_items = [
        ("🏠", "首页"),
        ("👥", "客户工作台"),
        ("⚙️", "设置"),
    ]

    for icon, label in nav_items:
        is_active = st.session_state['current_page'] == label
        btn_style = (
            "width:100%;text-align:left;padding:10px 16px;border:none;border-radius:8px;"
            "font-size:15px;cursor:pointer;transition:all 0.2s;margin-bottom:4px;"
        )
        if is_active:
            btn_style += "background:#3b82f6;color:white;font-weight:600;"
        else:
            btn_style += "background:transparent;color:#475569;"

        if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
            st.session_state['current_page'] = label
            for k in ['ws_selected_id', 'ws_show_import', 'ws_new_customer', 'ws_edit_id']:
                st.session_state.pop(k, None)
            st.rerun()

    st.markdown("---")
    st.caption("PPE客户开发管理系统 v4.0")

page = st.session_state['current_page']

if page == "首页":
    render_home_page()
elif page == "客户工作台":
    render_workspace()
elif page == "设置":
    render_settings()
