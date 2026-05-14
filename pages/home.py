import streamlit as st
import pandas as pd
from datetime import datetime, date
from database.db import Database

db = Database()


def render_home_page():
    st.markdown("""
    <h1 style="margin-bottom:0;">📊 PPE客户开发工作区</h1>
    <p style="color:#64748b;margin-top:0;">一站式管理外贸客户、开发邮件与背景调研</p>
    """, unsafe_allow_html=True)

    df, err = db.get_all_customers()
    if err:
        st.error("数据加载失败")
        return

    total = len(df)
    a_grade = len(df[df['customer_grade'] == 'A']) if not df.empty else 0
    b_grade = len(df[df['customer_grade'] == 'B']) if not df.empty else 0
    pending = len(df[df['development_status'] == '初次开发']) if not df.empty else 0
    quoted = len(df[df['development_status'] == '已报价']) if not df.empty else 0
    sample = len(df[df['development_status'] == '样品阶段']) if not df.empty else 0

    # ===== 今日待跟进（真实计算）=====
    today = date.today()
    due_count = 0
    overdue_count = 0
    overdue_customers = []
    if not df.empty:
        for _, row in df.iterrows():
            fud = row.get('follow_up_date')
            if fud and pd.notna(fud):
                try:
                    fud_date = pd.to_datetime(fud).date()
                    if fud_date <= today:
                        due_count += 1
                        if fud_date < today:
                            overdue_count += 1
                            overdue_customers.append({
                                'id': row['id'],
                                'name': row['company_name'],
                                'date': fud_date,
                                'status': row['development_status'],
                                'grade': row['customer_grade'],
                            })
                except Exception:
                    pass

    # ===== 指标卡片 =====
    def go(filter_key):
        st.session_state['current_page'] = "客户管理"
        st.session_state['home_filter'] = filter_key

    cols = st.columns(4)
    with cols[0]:
        st.button(f"👥  总客户数  {total}", key="metric_total", use_container_width=True,
                  on_click=go, args=("all",))
    with cols[1]:
        st.button(f"⭐  A级客户  {a_grade}", key="metric_a", use_container_width=True,
                  on_click=go, args=("grade_A",))
    with cols[2]:
        st.button(f"📋  B级客户  {b_grade}", key="metric_b", use_container_width=True,
                  on_click=go, args=("grade_B",))
    with cols[3]:
        st.button(f"🆕  待开发  {pending}", key="metric_pending", use_container_width=True,
                  on_click=go, args=("pending",))

    cols2 = st.columns(3)
    with cols2[0]:
        st.button(f"📨  已报价  {quoted}", key="metric_quoted", use_container_width=True,
                  on_click=go, args=("quoted",))
    with cols2[1]:
        st.button(f"📦  样品阶段  {sample}", key="metric_sample", use_container_width=True,
                  on_click=go, args=("sample",))
    with cols2[2]:
        label = f"📅  今日待跟进  {due_count}"
        if overdue_count > 0:
            label = f"🔔  今日待跟进  {due_count}（逾期{overdue_count}）"
        st.button(label, key="metric_followup", use_container_width=True,
                  on_click=go, args=("followup",))

    # ===== 逾期跟进提醒 =====
    st.markdown("---")
    if overdue_customers:
        overdue_customers.sort(key=lambda x: x['date'])
        st.subheader(f"🚨 逾期未跟进客户（{overdue_count} 位）")
        for c in overdue_customers:
            days = (today - c['date']).days
            grade = str(c['grade'])
            grade_label = f"{grade}级" if grade in ('A', 'B', 'C') else grade
            st.markdown(f"""
            <div style="background:#fef2f2;padding:0.6rem 1rem;border-radius:8px;
                        border-left:3px solid #ef4444;margin-bottom:4px;
                        display:flex;justify-content:space-between;align-items:center;">
                <span style="font-weight:600;color:#1e293b;">{c['name'][:50]}</span>
                <span style="color:#dc2626;font-weight:600;">逾期{days}天</span>
                <span style="font-size:0.8rem;color:#64748b;">{grade_label} | {c['status']}</span>
            </div>
            """, unsafe_allow_html=True)
            cc1, cc2 = st.columns([1, 10])
            with cc1:
                if st.button("📋", key=f"due_{c['id']}", help="查看详情"):
                    st.session_state['selected_customer'] = c['id']
                    st.session_state['current_page'] = "客户管理"
                    st.rerun()
    else:
        st.success("🎉 暂无逾期客户，干得漂亮！")

    # ===== 最近新增客户 =====
    st.markdown("---")
    st.subheader("📈 最近新增客户")
    if not df.empty:
        display_df = df[['company_name', 'country', 'customer_grade', 'development_status', 'assigned_to', 'created_at']].head(10).copy()
        display_df.columns = ['公司名称', '国家', '等级', '开发状态', '负责人', '创建时间']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无客户数据，快去添加第一个客户吧！")

    st.markdown("---")

    # ===== 快速操作 =====
    st.subheader("📌 快速操作")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("➕ 新增客户", use_container_width=True):
            st.session_state['show_add_form'] = True
            st.session_state['current_page'] = "客户管理"
            st.rerun()
    with c2:
        if st.button("🤖 生成开发邮件", use_container_width=True):
            st.session_state['current_page'] = "AI邮件生成"
            st.rerun()
    with c3:
        if st.button("🔍 客户背景研究", use_container_width=True):
            st.session_state['current_page'] = "客户背景研究"
            st.rerun()
