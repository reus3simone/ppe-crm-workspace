import streamlit as st
import pandas as pd
import os
import glob
import html
from datetime import datetime, date, timedelta
from database.db import Database

db = Database()


def render_home_page():
    st.markdown("""
    <h1 style="margin-bottom:0;">📊 PPE客户开发工作区</h1>
    <p style="color:#64748b;margin-top:0;">一站式管理外贸客户、开发邮件与背景调研</p>
    """, unsafe_allow_html=True)

    # 加载数据（附带跟进统计）
    df, err = db.get_all_customers_with_stats()
    if err:
        st.error("数据加载失败")
        return

    today = date.today()

    # ===== 🥉 一行全局概览 =====
    total = len(df)
    a_grade = len(df[df['customer_grade'] == 'A']) if not df.empty else 0
    active_dev = len(df[df['development_status'].isin(['已报价', '样品阶段'])]) if not df.empty else 0
    dormant_count = 0
    if not df.empty:
        dormant_count = df[df['last_follow_up_date'].apply(
            lambda x: (pd.to_datetime(x).date() if pd.notna(x) else None)
        ).apply(
            lambda d: (d is not None and (today - d).days > 60)
        )].shape[0]
    st.markdown(f"""
    <div style="background:#f8fafc;padding:0.5rem 1rem;border-radius:8px;border:1px solid #eef1f5;
                font-size:0.85rem;color:#475569;margin-bottom:1rem;">
        📊 总览：客户 <strong>{total}</strong> ｜ A级 <strong>{a_grade}</strong> ｜ 推进中 <strong>{active_dev}</strong> ｜ 沉睡 <strong>{dormant_count}</strong>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.info("暂无客户数据，快去添加第一个客户吧！")
        # 即使没客户也展示快速操作入口
        with st.expander("📌 快速操作", expanded=True):
            _render_quick_actions()
        return

    # ===== 分析每个客户的行动状态 =====
    urgent_list = []    # 🔥 今天必须处理
    secondary_list = [] # ⚡ 次优先

    for _, row in df.iterrows():
        cid = row['id']
        name = row['company_name']
        grade = str(row.get('customer_grade', 'C'))
        status = str(row.get('development_status', ''))
        grade_label = f"{grade}级" if grade in ('A', 'B', 'C') else grade

        # 健康度
        health = db.get_customer_health(row.get('last_follow_up_date'))

        # 1. 检查 follow_up_date（手动设置的跟进日）
        fud = row.get('follow_up_date')
        manual_due = None
        if fud and pd.notna(fud):
            try:
                manual_due = pd.to_datetime(fud).date()
            except Exception:
                pass

        # 2. SOP 自动算的跟进日
        next_date, next_msg = db.calculate_next_follow_up(cid)

        # 判断是否紧急
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

        # 判断次优先
        is_secondary = False
        if not is_urgent:
            if next_date and 0 < (next_date - today).days <= 3:
                is_secondary = True
                reason = f"{next_msg}（{(next_date - today).days}天后）"
            elif health['status'] == 'cooling':
                is_secondary = True
                reason = f"{health['label']}（{health['label']}中）"

        entry = {
            'id': cid,
            'name': name,
            'grade': grade_label,
            'grade_raw': grade,
            'status': status,
            'health': health,
            'reason': reason,
            'manual_due': manual_due,
            'next_date': next_date,
            'next_msg': next_msg,
        }

        if is_urgent:
            urgent_list.append(entry)
        elif is_secondary:
            secondary_list.append(entry)

    # 排序：逾期 > 今日 > A级优先
    def sort_key(e):
        due_sort = 0
        if e['manual_due'] and e['manual_due'] < today:
            due_sort = -(today - e['manual_due']).days  # 逾期越久越前
        elif e['manual_due'] and e['manual_due'] == today:
            due_sort = 0
        else:
            due_sort = 999
        grade_sort = 0 if e['grade_raw'] == 'A' else (1 if e['grade_raw'] == 'B' else 2)
        return (due_sort, grade_sort)

    urgent_list.sort(key=sort_key)
    secondary_list.sort(key=lambda e: (
        0 if e['grade_raw'] == 'A' else 1 if e['grade_raw'] == 'B' else 2
    ))

    # ===== 🥇 今天必须处理 =====
    if urgent_list:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="font-size:1.2rem;">🔥</span>
            <span style="font-weight:700;font-size:1.05rem;color:#1e293b;">今天必须处理</span>
            <span style="background:#fef2f2;color:#dc2626;padding:0 10px;border-radius:10px;font-size:0.75rem;font-weight:600;">{}</span>
        </div>
        """.format(len(urgent_list)), unsafe_allow_html=True)

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
                    <span style="color:#64748b;font-size:0.8rem;">{c['status']}</span>
                    <span style="color:#dc2626;font-weight:600;font-size:0.85rem;">{c['reason']}</span>
                    <a href="#" onclick="return false;" style="font-size:0.8rem;color:#3b82f6;text-decoration:none;">查看 →</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            cc1, cc2 = st.columns([1, 12])
            with cc1:
                if st.button("📋", key=f"urgent_{c['id']}", help="查看详情"):
                    st.session_state['selected_customer'] = c['id']
                    st.session_state['current_page'] = "客户管理"
                    st.rerun()
    else:
        st.success("🎉 今天没有待处理的客户，干得漂亮！")

    # ===== 🥈 次优先 =====
    if secondary_list:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:8px;margin:12px 0 8px 0;">
            <span style="font-size:1.2rem;">⚡</span>
            <span style="font-weight:700;font-size:1.05rem;color:#1e293b;">次优先</span>
            <span style="background:#f8fafc;color:#64748b;padding:0 10px;border-radius:10px;font-size:0.75rem;font-weight:600;">{}</span>
        </div>
        """.format(len(secondary_list)), unsafe_allow_html=True)

        for c in secondary_list:
            st.markdown(f"""
            <div style="background:white;padding:0.5rem 1rem;border-radius:8px;
                        border:1px solid #eef1f5;margin-bottom:3px;
                        display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-weight:600;color:#1e293b;font-size:0.9rem;">{html.escape(c['name'][:50])}</span>
                    <span style="margin-left:6px;font-size:0.7rem;background:#e6f7ec;color:#15803d;padding:1px 8px;border-radius:8px;">{c['grade']}</span>
                    <span style="margin-left:4px;font-size:0.75rem;color:#64748b;">{c['health']['icon']} {c['health']['label']}</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="color:#64748b;font-size:0.8rem;">{c['status']}</span>
                    <span style="color:#b45309;font-size:0.8rem;">{c['reason']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ===== 📦 折叠信息区 =====

    # 全局活动流（默认折叠）
    with st.expander("📈 全局活动流"):
        feed_df, feed_err = db.get_global_activity_feed(20)
        if feed_err:
            st.error(f"加载失败：{feed_err}")
        elif feed_df.empty:
            st.info("暂无活动记录")
        else:
            today_str = date.today().strftime('%Y-%m-%d')
            yesterday_str = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
            groups = {"今天": [], "昨天": [], "本周": [], "更早": []}
            for _, e in feed_df.iterrows():
                try:
                    day = pd.to_datetime(e['created_at']).strftime('%Y-%m-%d')
                except Exception:
                    day = ""
                if day == today_str:
                    groups["今天"].append(e)
                elif day == yesterday_str:
                    groups["昨天"].append(e)
                elif (date.today() - pd.to_datetime(e['created_at']).date()).days < 7:
                    groups["本周"].append(e)
                else:
                    groups["更早"].append(e)

            for group_name in ["今天", "昨天", "本周", "更早"]:
                items = groups[group_name]
                if not items:
                    continue
                st.markdown(f"**{group_name}**")
                for e in items:
                    cname = html.escape(str(e.get('company_name', '未知客户')))
                    etype = html.escape(str(e['event_type']))
                    econtent = html.escape(str(e['event_content'] or ''))
                    try:
                        etime = pd.to_datetime(e['created_at']).strftime('%H:%M')
                    except Exception:
                        etime = ""
                    grade = str(e.get('customer_grade', ''))
                    g_tag = f"<span class='grade-{grade.lower()}' style='font-size:0.65rem;'>{grade}级</span>" if grade in ('A','B','C') else ""
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;gap:8px;padding:4px 0;
                                font-size:0.85rem;border-bottom:1px solid #f1f5f9;">
                        <span style="color:#94a3b8;font-size:0.75rem;min-width:40px;">{etime}</span>
                        <span style="font-weight:600;color:#1e293b;">{cname}</span>
                        {g_tag}
                        <span style="color:#3b82f6;font-size:0.8rem;">{etype}</span>
                        <span style="color:#64748b;font-size:0.8rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:300px;">{econtent[:60]}</span>
                    </div>
                    """, unsafe_allow_html=True)

    # 快速操作（默认折叠）
    with st.expander("📌 快速操作"):
        _render_quick_actions()

    # 数据备份与恢复（默认折叠）
    with st.expander("💾 数据备份与恢复"):
        _render_backup_section()


def _render_quick_actions():
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("➕ 新增客户", use_container_width=True):
            st.session_state['show_add_form'] = True
            st.session_state['current_page'] = "客户管理"
            st.rerun()
    with c2:
        if st.button("📧 跟进邮件工坊", use_container_width=True):
            st.session_state['current_page'] = "跟进邮件工坊"
            st.rerun()
    with c3:
        if st.button("🔍 客户背景研究", use_container_width=True):
            st.session_state['current_page'] = "客户背景研究"
            st.rerun()


def _render_backup_section():
    _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _backup_dir = os.path.join(_base_dir, "assets")
    os.makedirs(_backup_dir, exist_ok=True)

    def _list_backups():
        files = glob.glob(os.path.join(_backup_dir, "客户备份_*.xlsx"))
        files.sort(reverse=True)
        return files[:3]

    bc1, bc2 = st.columns(2)
    with bc1:
        st.caption("备份全部数据：客户、邮件历史、跟进记录、模板、系统设置")
        if st.button("📀 手动全量备份", type="primary", use_container_width=True):
            now = datetime.now()
            fname = f"客户备份_{now.strftime('%Y%m%d_%H%M')}.xlsx"
            fpath = os.path.join(_backup_dir, fname)
            ok, err = db.backup_data(fpath)
            if ok:
                st.success(f"✅ 全量备份成功：{fname}")
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
