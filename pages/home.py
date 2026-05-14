
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.db import Database

# 全局数据库实例
db = Database()

def get_statistics():
    """全空值安全统计，无数据不崩溃"""
    df, _ = db.get_all_customers()
    if df.empty:
        return {
            'total': 0, 'grade_a': 0, 'grade_b': 0, 'grade_c': 0,
            'status_active': 0, 'status_pending': 0, 'status_rejected': 0,
            'countries': {}, 'conversion_rate': 0
        }

    stats = {
        'total': len(df),
        'grade_a': len(df[df['customer_grade'] == 'A']),
        'grade_b': len(df[df['customer_grade'] == 'B']),
        'grade_c': len(df[df['customer_grade'] == 'C']),
        'status_active': len(df[df['status'] == '正在跟进']),
        'status_pending': len(df[df['status'] == '备选']),
        'status_rejected': len(df[df['status'] == '拒绝']),
        'countries': df['country'].value_counts().to_dict(),
        'conversion_rate': round(len(df[df['customer_grade'] == 'A']) / len(df) * 100, 1)
    }
    return stats

def get_follow_up_reminders():
    """跟进提醒筛选，兼容空日期、过期数据"""
    df, _ = db.get_all_customers()
    today = datetime.now().date()
    week_end = today + timedelta(days=7)
    df_clean = df.copy()

    # 日期格式标准化，空值过滤
    df_clean['follow_up_date'] = pd.to_datetime(df_clean['follow_up_date'], errors='coerce').dt.date

    today_follow = df_clean[
        (df_clean['follow_up_date'] == today) &
        (df_clean['status'] != '拒绝')
    ].sort_values('follow_up_date')

    week_follow = df_clean[
        (df_clean['follow_up_date'] > today) &
        (df_clean['follow_up_date'] <= week_end) &
        (df_clean['status'] != '拒绝')
    ].sort_values('follow_up_date')

    overdue = df_clean[
        (df_clean['follow_up_date'] < today) &
        (df_clean['status'] != '拒绝') &
        (df_clean['follow_up_date'].notna())
    ].sort_values('follow_up_date')

    return {'today': today_follow, 'week': week_follow, 'overdue': overdue}

def render_stat_card(title, value, color="#3b82f6"):
    """统计卡片渲染"""
    st.markdown(f"""
    <div class="stat-card" style="border-left-color: {color};">
        <h3>{title}</h3>
        <div class="value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def render_reminder_customer(row, is_overdue=False):
    """跟进提醒卡片，空联系人兼容显示"""
    css_class = "reminder-card urgent" if is_overdue else "reminder-card"
    contact_name = row['contact_person'] if pd.notna(row['contact_person']) else "暂无联系人"
    contact_email = row['email'] if pd.notna(row['email']) else "暂无邮箱"

    st.markdown(f"""
    <div class="{css_class}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>{row['company_name']}</strong>
                <span class="grade-{row['customer_grade'].lower()}" style="margin-left: 0.5rem;">{row['customer_grade']}级</span>
            </div>
            <small>跟进日期: {row['follow_up_date']}</small>
        </div>
        <div style="margin-top: 0.5rem; font-size: 0.875rem; color: #64748b;">
            {contact_name} | {contact_email}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_home_page():
    st.title("📊 PPE客户开发工作区")
    st.markdown("---")
    st.header("📈 数据概览")
    stats = get_statistics()

    # 第一行统计卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_stat_card("总客户数", stats['total'], "#3b82f6")
    with col2:
        render_stat_card("A级客户", stats['grade_a'], "#10b981")
    with col3:
        render_stat_card("正在跟进", stats['status_active'], "#f59e0b")
    with col4:
        render_stat_card("转化率", f"{stats['conversion_rate']}%", "#8b5cf6")

    # 第二行统计卡片
    col1, col2, col3 = st.columns(3)
    with col1:
        render_stat_card("B级客户", stats['grade_b'], "#3b82f6")
    with col2:
        render_stat_card("C级客户", stats['grade_c'], "#f59e0b")
    with col3:
        render_stat_card("已拒绝", stats['status_rejected'], "#ef4444")

    st.markdown("---")
    st.subheader("🎯 A级客户质量占比")
    if stats['total'] > 0:
        st.progress(stats['grade_a'] / stats['total'])
        st.caption(f"A级客户 {stats['grade_a']} 家 / 总客户 {stats['total']} 家")
    else:
        st.info("暂无客户数据，无法计算质量占比")

    st.markdown("---")
    reminders = get_follow_up_reminders()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔔 今日需跟进")
        if not reminders['overdue'].empty:
            st.markdown("**⚠️ 已过期跟进任务**")
            for _, row in reminders['overdue'].iterrows():
                render_reminder_customer(row, is_overdue=True)
        if reminders['today'].empty:
            st.info("今日暂无待跟进客户")
        else:
            for _, row in reminders['today'].iterrows():
                render_reminder_customer(row)

    with col2:
        st.subheader("📅 本周待跟进")
        if reminders['week'].empty:
            st.info("本周暂无待跟进客户")
        else:
            for _, row in reminders['week'].iterrows():
                render_reminder_customer(row)

    st.markdown("---")
    st.subheader("🌍 客户国家分布")
    if stats['countries']:
        country_df = pd.DataFrame({
            '国家': list(stats['countries'].keys()),
            '客户数量': list(stats['countries'].values())
        })
        st.bar_chart(country_df.set_index('国家'), height=300, use_container_width=True)
    else:
        st.info("暂无国家分布数据")
