import streamlit as st
import pandas as pd
from datetime import datetime
from database.db import Database

db = Database()

def get_follow_up_reminders():
    df, err = db.get_all_customers()
    if err or df.empty:
        return []
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        df['follow_up_date'] = pd.to_datetime(df['follow_up_date'], errors='coerce').dt.strftime('%Y-%m-%d')
        df_clean = df[df['follow_up_date'].notna()]
        reminders = df_clean[df_clean['follow_up_date'] <= today].to_dict('records')
        return reminders
    except Exception:
        return []

def render_home_page():
    st.title("📊 PPE客户开发工作区")
    st.markdown("---")

    df, err = db.get_all_customers()
    if err:
        st.error("数据加载失败")
        return

    total = len(df)
    a_grade = len(df[df['customer_grade'] == 'A'])
    b_grade = len(df[df['customer_grade'] == 'B'])
    pending = len(df[df['development_status'] == '初次开发'])
    quoted = len(df[df['development_status'] == '已报价'])
    sample = len(df[df['development_status'] == '样品阶段'])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总客户数", total)
    col2.metric("A级客户", a_grade)
    col3.metric("B级客户", b_grade)
    col4.metric("待开发", pending)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("已报价", quoted)
    col2.metric("样品阶段", sample)
    reminders = get_follow_up_reminders()
    col3.metric("今日待跟进", len(reminders))

    if reminders:
        st.markdown("---")
        st.warning("⚠️ 今日待跟进客户")
        for c in reminders:
            st.write(f"• {c['company_name']} | 上次跟进：{c.get('follow_up_date', '')}")

    st.markdown("---")
    st.subheader("📈 最近新增客户")
    if not df.empty:
        st.dataframe(
            df[['company_name', 'country', 'customer_grade', 'development_status', 'assigned_to', 'created_at']].head(10),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("暂无客户数据，快去添加第一个客户吧！")

    st.markdown("---")
    st.subheader("📌 快速操作")
    col1, col2, col3 = st.columns(3)
    if col1.button("➕ 新增客户", use_container_width=True):
        st.session_state['show_add_form'] = True
        st.session_state['current_page'] = "客户管理"
        st.rerun()
    if col2.button("🤖 生成开发邮件", use_container_width=True):
        st.session_state['current_page'] = "AI邮件生成"
        st.rerun()
    if col3.button("🔍 客户背景研究", use_container_width=True):
        st.session_state['current_page'] = "客户背景研究"
        st.rerun()
