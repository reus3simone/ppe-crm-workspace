import streamlit as st
import pandas as pd
import os
import glob
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

    # ===== 数据备份与恢复 =====
    st.markdown("---")
    st.subheader("💾 数据备份与恢复")

    _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _backup_dir = os.path.join(_base_dir, "assets")
    os.makedirs(_backup_dir, exist_ok=True)

    def _list_backups():
        files = glob.glob(os.path.join(_backup_dir, "客户备份_*.xlsx"))
        files.sort(reverse=True)
        return files[:3]

    bc1, bc2 = st.columns(2)
    with bc1:
        st.caption("定期备份客户数据，防止意外丢失")
        if st.button("📀 手动备份数据", type="primary", use_container_width=True):
            now = datetime.now()
            fname = f"客户备份_{now.strftime('%Y%m%d_%H%M')}.xlsx"
            fpath = os.path.join(_backup_dir, fname)
            ok, err = db.backup_data(fpath)
            if ok:
                st.success(f"✅ 备份成功：{fname}")
                all_bk = sorted(glob.glob(os.path.join(_backup_dir, "客户备份_*.xlsx")), reverse=True)
                for f in all_bk[3:]:
                    try:
                        os.remove(f)
                    except Exception:
                        pass
                st.info("已自动清理旧备份，保留最新 3 个")
                st.rerun()
            else:
                st.error(f"❌ 备份失败：{err}")

    with bc2:
        backups = _list_backups()
        if backups:
            bnames = [os.path.basename(f) for f in backups]
            st.selectbox("选择备份文件恢复", bnames, key="restore_select")

            if st.button("🔄 恢复数据", use_container_width=True):
                st.session_state['confirm_restore'] = True

            if st.session_state.get('confirm_restore', False):
                st.warning("⚠️ 恢复操作将覆盖当前所有客户数据，此操作不可撤销！请谨慎操作。")
                r1, r2 = st.columns(2)
                with r1:
                    if st.button("✅ 确认恢复", key="confirm_restore_btn"):
                        sel = st.session_state['restore_select']
                        ok, msg = db.restore_data(os.path.join(_backup_dir, sel))
                        if ok:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ {msg}")
                            remaining = [b for b in bnames if b != sel]
                            if remaining:
                                st.info(f"💡 可尝试选择其他备份：{'、'.join(remaining)}")
                        st.session_state['confirm_restore'] = False
                        st.rerun()
                with r2:
                    if st.button("❌ 取消", key="cancel_restore_btn"):
                        st.session_state['confirm_restore'] = False
                        st.rerun()
        else:
            st.info("暂无备份文件，请先点击左侧按钮进行备份")
