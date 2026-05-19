import streamlit as st
import pandas as pd
import html
from datetime import datetime, date, timedelta
from database.db import Database

db = Database()


def render_home_page():
    st.markdown("""
    <h1 style="margin-bottom:0;">📊 PPE客户开发工作区</h1>
    <p style="color:#64748b;margin-top:0;">今天谁该跟进了？</p>
    """, unsafe_allow_html=True)

    df, err = db.get_all_customers_with_stats()
    if err:
        st.error("数据加载失败")
        return

    today = date.today()

    # 概览行
    total = len(df)
    a_count = len(df[df['customer_grade'] == 'A']) if not df.empty else 0
    active = len(df[df['development_status'].isin(['已报价', '样品阶段'])]) if not df.empty else 0

    overdue_count = 0
    if not df.empty:
        def _is_overdue(d):
            if pd.isna(d):
                return False
            try:
                return (today - pd.to_datetime(d).date()).days > 0
            except Exception:
                return False
        overdue_count = df[df['follow_up_date'].apply(_is_overdue)].shape[0]

    st.markdown(f"""
    <div style="background:#f8fafc;padding:0.5rem 1rem;border-radius:8px;border:1px solid #eef1f5;
                font-size:0.85rem;color:#475569;margin-bottom:1rem;">
        总客户 <strong>{total}</strong> ｜ A级 <strong>{a_count}</strong> ｜
        推进中 <strong>{active}</strong> ｜
        <span style="color:#dc2626;">逾期 <strong>{overdue_count}</strong></span>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.info("暂无客户数据，去「客户工作台」添加第一个客户吧！")
        if st.button("👥 去客户工作台"):
            st.session_state['current_page'] = "客户工作台"
            st.rerun()
        return

    # 分析每个客户
    urgent_list = []
    secondary_list = []

    for _, row in df.iterrows():
        cid = row['id']
        name = row['company_name']
        grade = str(row.get('customer_grade', 'C'))
        status = str(row.get('development_status', ''))
        grade_label = f"{grade}级" if grade in ('A', 'B', 'C') else grade

        health = db.get_customer_health(row.get('last_follow_up_date'))

        # 手动跟进日
        fud = row.get('follow_up_date')
        manual_due = None
        if fud and pd.notna(fud):
            try:
                manual_due = pd.to_datetime(fud).date()
            except Exception:
                pass

        # SOP 自动计算
        next_date, next_msg = db.calculate_next_follow_up(cid)

        is_urgent = False
        reason = ""

        if manual_due and manual_due <= today:
            is_urgent = True
            if manual_due < today:
                days = (today - manual_due).days
                reason = f"逾期{days}天"
            else:
                reason = "今日跟进"

        if next_date and next_date <= today and not is_urgent:
            is_urgent = True
            reason = next_msg

        is_secondary = False
        if not is_urgent:
            if next_date and 0 < (next_date - today).days <= 3:
                is_secondary = True
                reason = f"{next_msg}（{(next_date - today).days}天后）"
            elif health['status'] == 'cooling':
                is_secondary = True
                reason = "变凉中"

        entry = {
            'id': cid, 'name': name, 'grade': grade_label,
            'grade_raw': grade, 'status': status,
            'health': health, 'reason': reason,
        }

        if is_urgent:
            urgent_list.append(entry)
        elif is_secondary:
            secondary_list.append(entry)

    # 排序：逾期越久越前，同逾期A级优先
    urgent_list.sort(key=lambda e: (
        -(e.get('_overdue_days', 0)),
        0 if e['grade_raw'] == 'A' else 1 if e['grade_raw'] == 'B' else 2
    ))

    # 计算逾期天数
    for e in urgent_list:
        cid = e['id']
        c, _ = db.get_customer(cid)
        if c and c.get('follow_up_date'):
            try:
                fd = pd.to_datetime(c['follow_up_date']).date()
                e['_overdue_days'] = (today - fd).days
            except Exception:
                e['_overdue_days'] = 0
        else:
            e['_overdue_days'] = 0

    urgent_list.sort(key=lambda e: (
        -e['_overdue_days'],
        0 if e['grade_raw'] == 'A' else 1 if e['grade_raw'] == 'B' else 2
    ))

    secondary_list.sort(key=lambda e: (
        0 if e['grade_raw'] == 'A' else 1 if e['grade_raw'] == 'B' else 2
    ))

    # ===== 🔥 今天必须处理 =====
    if urgent_list:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="font-size:1.2rem;">🔥</span>
            <span style="font-weight:700;font-size:1.05rem;color:#1e293b;">今天必须处理</span>
            <span style="background:#fef2f2;color:#dc2626;padding:0 10px;border-radius:10px;font-size:0.75rem;font-weight:600;">{len(urgent_list)}</span>
        </div>
        """, unsafe_allow_html=True)

        for c in urgent_list:
            bg = "#fef2f2" if "逾期" in c['reason'] else "#fef9e7"
            border = "#ef4444" if "逾期" in c['reason'] else "#f59e0b"
            st.markdown(f"""
            <div style="background:{bg};padding:0.6rem 1rem;border-radius:8px;
                        border-left:4px solid {border};margin-bottom:4px;
                        display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-weight:600;color:#1e293b;">{html.escape(c['name'][:50])}</span>
                    <span style="margin-left:6px;font-size:0.75rem;background:#e6f7ec;color:#15803d;padding:1px 8px;border-radius:8px;">{c['grade']}</span>
                </div>
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="color:#64748b;font-size:0.8rem;">{c['health']['icon']} {c['health']['label']}</span>
                    <span style="color:#dc2626;font-weight:600;font-size:0.85rem;">{c['reason']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("去处理 →", key=f"go_{c['id']}", use_container_width=False):
                st.session_state['current_page'] = "客户工作台"
                st.session_state['ws_selected_id'] = c['id']
                st.rerun()
    else:
        st.success("🎉 今天没有待处理的客户，干得漂亮！")

    # ===== ⚡ 次优先 =====
    if secondary_list:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;margin:16px 0 8px 0;">
            <span style="font-size:1.2rem;">⚡</span>
            <span style="font-weight:700;font-size:1.05rem;color:#1e293b;">次优先</span>
            <span style="background:#f8fafc;color:#64748b;padding:0 10px;border-radius:10px;font-size:0.75rem;font-weight:600;">{len(secondary_list)}</span>
        </div>
        """, unsafe_allow_html=True)

        for c in secondary_list:
            st.markdown(f"""
            <div style="background:white;padding:0.5rem 1rem;border-radius:8px;
                        border:1px solid #eef1f5;margin-bottom:3px;
                        display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-weight:600;font-size:0.9rem;color:#1e293b;">{html.escape(c['name'][:50])}</span>
                    <span style="margin-left:6px;font-size:0.7rem;background:#e6f7ec;color:#15803d;padding:1px 8px;border-radius:8px;">{c['grade']}</span>
                    <span style="margin-left:4px;font-size:0.75rem;color:#64748b;">{c['health']['icon']} {c['health']['label']}</span>
                </div>
                <div style="color:#b45309;font-size:0.8rem;">{c['reason']}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("去看看", key=f"sec_{c['id']}", use_container_width=False):
                st.session_state['current_page'] = "客户工作台"
                st.session_state['ws_selected_id'] = c['id']
                st.rerun()

    st.markdown("---")
    st.caption("去「客户工作台」查看全部客户 · 去「设置」管理团队和备份数据")
