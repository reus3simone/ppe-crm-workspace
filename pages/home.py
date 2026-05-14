import streamlit as st
import pandas as pd
from datetime import datetime
from database.db import Database

db = Database()

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
    with col1:
        st.metric("总客户数", total)
    with col2:
        st.metric("A级客户", a_grade, delta=f"占比 {round(a_grade/total*100, 1)}%" if total>0 else "0%")
    with col3:
        st.metric("B级客户", b_grade, delta=f"占比 {round(b_grade/total*100, 1)}%" if total>0 else "0%")
    with col4:
        st.metric("待开发", pending)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("已报价", quoted)
    with col2:
        st.metric("样品阶段", sample)
    with col3:
        today = datetime.now().strftime('%Y-%m-%d')
        today_follow = len(df[df['follow_up_date'] == today])
        st.metric("今日待跟进", today_follow)

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
    with col1:
        if st.button("➕ 新增客户", use_container_width=True):
            st.session_state['show_add_form'] = True
            st.session_state['current_page'] = "客户管理"
            st.rerun()
    with col2:
        if st.button("🤖 生成开发邮件", use_container_width=True):
            st.session_state['current_page'] = "AI邮件生成"
            st.rerun()
    with col3:
        if st.button("🔍 客户背景研究", use_container_width=True):
            st.session_state['current_page'] = "客户背景研究"
            st.rerun()
