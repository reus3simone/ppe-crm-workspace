import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 加载CSS
with open("assets/styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 导入页面
from pages.home import render_home_page
from pages.customers import render_customer_list, render_customer_detail, render_customer_form
from pages.ai_email import render_ai_email
from pages.research import render_research

# 页面配置
st.set_page_config(
    page_title="PPE客户开发工作区",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "PPE客户开发管理系统 v3.0"
    }
)

# 隐藏Streamlit自动生成的英文导航
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
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

# 侧边栏导航（纯中文）
with st.sidebar:
    st.title("📊 PPE客户开发")
    st.markdown("---")

    if st.button("🏠 首页", use_container_width=True):
        st.session_state['current_page'] = "首页"
        st.rerun()

    if st.button("👥 客户管理", use_container_width=True):
        st.session_state['current_page'] = "客户管理"
        st.rerun()

    if st.button("🤖 AI邮件生成", use_container_width=True):
        st.session_state['current_page'] = "AI邮件生成"
        st.rerun()

    if st.button("🔍 客户背景研究", use_container_width=True):
        st.session_state['current_page'] = "客户背景研究"
        st.rerun()

    st.markdown("---")
    st.caption("PPE客户开发管理系统 v3.0")

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
