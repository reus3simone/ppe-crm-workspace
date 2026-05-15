import streamlit as st
import sys
import os

# 页面配置 — 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="PPE客户开发工作区",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "PPE客户开发管理系统 v3.1"
    }
)

# 加载 CSS（使用绝对路径）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
css_path = os.path.join(BASE_DIR, "assets", "styles.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

sys.path.append(BASE_DIR)

# 导入页面
from pages.home import render_home_page
from pages.customers import render_customer_list, render_customer_detail, render_customer_form
from pages.ai_email import render_ai_email
from pages.research import render_research

# 隐藏 Streamlit 自动生成的英文导航
st.markdown("""
<style>
    [data-testid="stSidebarNav"] { display: none; }
</style>
""", unsafe_allow_html=True)

# Session State 初始化
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "首页"

if 'show_import' not in st.session_state:
    st.session_state['show_import'] = False

if 'show_add_form' not in st.session_state:
    st.session_state['show_add_form'] = False

if 'selected_customer' not in st.session_state:
    st.session_state['selected_customer'] = None

if 'edit_customer' not in st.session_state:
    st.session_state['edit_customer'] = None

if 'ai_email_customer' not in st.session_state:
    st.session_state['ai_email_customer'] = None

if 'research_customer' not in st.session_state:
    st.session_state['research_customer'] = None

if 'confirm_restore' not in st.session_state:
    st.session_state['confirm_restore'] = False

# 侧边栏导航
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
        ("👥", "客户管理"),
        ("🤖", "AI邮件生成"),
        ("🔍", "客户背景研究"),
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
            st.rerun()

    st.markdown("---")
    st.caption("PPE客户开发管理系统 v3.1")

# 页面路由
page = st.session_state['current_page']

if page == "首页":
    render_home_page()

elif page == "客户管理":
    if st.session_state.get('show_add_form'):
        render_customer_form(is_edit=False)
    elif st.session_state.get('edit_customer'):
        render_customer_form(is_edit=True)
    elif st.session_state.get('selected_customer'):
        render_customer_detail()
    else:
        render_customer_list()

elif page == "AI邮件生成":
    render_ai_email()

elif page == "客户背景研究":
    render_research()
