import streamlit as st
import pandas as pd
import html
from datetime import datetime, date, timedelta
from database.db import Database

db = Database()

# ── 国家 → 国旗 emoji ──
COUNTRY_FLAG = {
    'usa': '🇺🇸', 'united states': '🇺🇸', 'us': '🇺🇸', 'america': '🇺🇸',
    'uk': '🇬🇧', 'united kingdom': '🇬🇧', 'england': '🇬🇧', 'britain': '🇬🇧',
    'germany': '🇩🇪', 'deutschland': '🇩🇪',
    'france': '🇫🇷', 'french': '🇫🇷',
    'italy': '🇮🇹', 'italia': '🇮🇹',
    'spain': '🇪🇸', 'españa': '🇪🇸',
    'netherlands': '🇳🇱', 'holland': '🇳🇱',
    'belgium': '🇧🇪',
    'switzerland': '🇨🇭',
    'sweden': '🇸🇪',
    'norway': '🇳🇴',
    'denmark': '🇩🇰',
    'finland': '🇫🇮',
    'poland': '🇵🇱',
    'czech': '🇨🇿', 'czech republic': '🇨🇿',
    'australia': '🇦🇺',
    'canada': '🇨🇦',
    'japan': '🇯🇵',
    'south korea': '🇰🇷', 'korea': '🇰🇷',
    'brazil': '🇧🇷',
    'mexico': '🇲🇽',
    'uae': '🇦🇪', 'united arab emirates': '🇦🇪',
    'saudi arabia': '🇸🇦',
    'south africa': '🇿🇦',
    'india': '🇮🇳',
    'singapore': '🇸🇬',
    'malaysia': '🇲🇾',
    'thailand': '🇹🇭',
    'vietnam': '🇻🇳',
    'indonesia': '🇮🇩',
    'turkey': '🇹🇷', 'türkiye': '🇹🇷',
    'russia': '🇷🇺',
    'china': '🇨🇳',
}


def _flag(country):
    if not country:
        return ''
    c = country.strip().lower()
    for k, v in COUNTRY_FLAG.items():
        if k in c or c in k:
            return v
    return '🌍'


def render_home_page():
    st.markdown("""
    <div style="margin-bottom:0.5rem;">
        <span style="font-size:1.5rem;font-weight:700;color:#1e293b;">📊 PPE客户开发工作区</span>
        <span style="color:#94a3b8;font-size:0.85rem;margin-left:12px;">今天谁该跟进了？</span>
    </div>
    """, unsafe_allow_html=True)

    df, err = db.get_all_customers_with_stats()
    if err:
        st.error("数据加载失败")
        return

    today = date.today()

    # =========================================================
    # 1. 指标卡片 (4 个)
    # =========================================================
    total = len(df)
    a_count = len(df[df['customer_grade'] == 'A']) if not df.empty else 0
    b_count = len(df[df['customer_grade'] == 'B']) if not df.empty else 0
    c_count = len(df[df['customer_grade'] == 'C']) if not df.empty else 0
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

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.markdown(
            '<div class="metric-card"><div class="label">总客户数</div>'
            f'<div class="value">{total}</div>'
            f'<div class="sub">A {a_count} · B {b_count} · C {c_count}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with mc2:
        st.markdown(
            '<div class="metric-card"><div class="label">A 级 / B 级 / C 级</div>'
            f'<div class="value" style="font-size:1.1rem;">{a_count} / {b_count} / {c_count}</div>'
            f'<div class="sub">B 级占比最高</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with mc3:
        st.markdown(
            '<div class="metric-card"><div class="label">推进中客户</div>'
            f'<div class="value">{active}</div>'
            '<div class="sub">已报价 + 样品阶段</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with mc4:
        st.markdown(
            '<div class="metric-card"><div class="label">逾期跟进</div>'
            f'<div class="value" style="color:{("#ef4444" if overdue_count > 0 else "#1e293b")};">{overdue_count}</div>'
            f'<div class="sub" style="color:{("#ef4444" if overdue_count > 0 else "#94a3b8")};">'
            f'{"需尽快处理" if overdue_count > 0 else "全部按时"}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)

    # =========================================================
    # 2. 开发阶段分布 (5 个彩色卡片)
    # =========================================================
    if not df.empty:
        stage_keys = ["初次开发", "已发开发信", "已报价", "样品阶段", "已成交"]
        stage_labels = ["🆕 初次开发", "📧 已发开发信", "💬 已报价", "📦 样品阶段", "✅ 已成交"]
        stage_colors = ["#3b5fd9", "#b45309", "#15803d", "#7c3aed", "#be185d"]
        stage_bgs = ["#eef2ff", "#fef9e7", "#e6f7ec", "#ede9fe", "#fce7f3"]

        cols = st.columns(5)
        for i in range(5):
            with cols[i]:
                sk = stage_keys[i]
                if sk == "已发开发信":
                    cnt = df[df['development_status'].str.contains('已发', na=False) &
                              df['development_status'].str.contains('开发信', na=False)].shape[0]
                else:
                    cnt = df[df['development_status'] == sk].shape[0]

                st.markdown(
                    f'<div class="stage-card" style="background:{stage_bgs[i]};border-color:{stage_colors[i]}33;">'
                    f'<div class="count" style="color:{stage_colors[i]};">{cnt}</div>'
                    f'<div class="name" style="color:{stage_colors[i]};">{stage_labels[i]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button("查看 →", key=f"gostage_{i}", use_container_width=True,
                             help=f"去客户工作台查看{sk}客户"):
                    st.session_state['current_page'] = "客户工作台"
                    st.session_state['ws_filter_tag'] = sk
                    for k in ['ws_selected_id', 'ws_show_import', 'ws_new_customer', 'ws_edit_id']:
                        st.session_state.pop(k, None)
                    st.rerun()

    if df.empty:
        st.info("暂无客户数据，去「客户工作台」添加第一个客户吧！")
        if st.button("👥 去客户工作台"):
            st.session_state['current_page'] = "客户工作台"
            st.rerun()
        return

    st.markdown('<div style="height:0.8rem;"></div>', unsafe_allow_html=True)

    # =========================================================
    # 3. 分析每个客户 → 紧急 / 次优先
    # =========================================================
    urgent_list = []
    secondary_list = []

    for _, row in df.iterrows():
        cid = row['id']
        name = row['company_name']
        country = str(row.get('country', '') or '')
        grade = str(row.get('customer_grade', 'C'))
        grade_label = f"{grade}级" if grade in ('A', 'B', 'C') else grade
        health = db.get_customer_health(row.get('last_follow_up_date'))

        fud = row.get('follow_up_date')
        manual_due = None
        if fud and pd.notna(fud):
            try:
                manual_due = pd.to_datetime(fud).date()
            except Exception:
                pass

        next_date, next_msg = db.calculate_next_follow_up(cid)

        is_urgent = False
        reason = ""
        overdue_days = 0

        if manual_due and manual_due <= today:
            is_urgent = True
            overdue_days = (today - manual_due).days
            if overdue_days == 0:
                reason = "今日跟进"
            else:
                reason = f"逾期{overdue_days}天"

        if next_date and next_date <= today and not is_urgent:
            is_urgent = True
            overdue_days = (today - next_date).days
            reason = next_msg

        is_secondary = False
        if not is_urgent:
            if manual_due and manual_due > today:
                pass
            elif next_date and 0 < (next_date - today).days <= 3:
                is_secondary = True
                reason = f"{next_msg}（{(next_date - today).days}天后）"
            elif health['status'] == 'cooling':
                is_secondary = True
                reason = "变凉中"

        follow_up_str = ''
        if manual_due:
            follow_up_str = manual_due.isoformat()
        elif next_date:
            follow_up_str = next_date.isoformat()

        entry = {
            'id': cid, 'name': name, 'country': country, 'grade': grade_label,
            'grade_raw': grade, 'follow_up_date': follow_up_str,
            'overdue_days': overdue_days, 'reason': reason,
        }

        if is_urgent:
            urgent_list.append(entry)
        elif is_secondary:
            secondary_list.append(entry)

    # 排序：逾期越久越前，同逾期 A 优先
    urgent_list.sort(key=lambda e: (
        -e['overdue_days'],
        0 if e['grade_raw'] == 'A' else 1 if e['grade_raw'] == 'B' else 2
    ))
    secondary_list.sort(key=lambda e: (
        0 if e['grade_raw'] == 'A' else 1 if e['grade_raw'] == 'B' else 2
    ))

    # =========================================================
    # 4. 🔥 今天必须处理
    # =========================================================
    if urgent_list:
        st.markdown(
            f'<div class="section-header">'
            f'<span style="font-size:1.2rem;">🔥</span>'
            f'<span class="title">今天必须处理</span>'
            f'<span class="badge" style="background:#fef2f2;color:#dc2626;">{len(urgent_list)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for c in urgent_list:
            is_overdue = "逾期" in c['reason']
            bg = "#fef2f2" if is_overdue else "#fffbeb"
            border = "#ef4444" if is_overdue else "#f59e0b"
            overdue_color = "#dc2626" if is_overdue else "#d97706"

            follow_display = c['follow_up_date'] if c['follow_up_date'] else '—'
            flag = _flag(c['country'])

            st.markdown(
                f'<div class="urgent-row" style="background:{bg};border-left-color:{border};">'
                f'<div class="left">'
                f'<span class="name">{html.escape(c["name"][:45])}</span>'
                f'<span style="font-size:0.85rem;">{flag} {html.escape(c["country"][:15])}</span>'
                f'<span class="tag grade-{c["grade_raw"].lower()}">{html.escape(c["grade"])}</span>'
                f'</div>'
                f'<div class="right">'
                f'<span class="date">跟进 {follow_display}</span>'
                f'<span class="overdue" style="color:{overdue_color};">{html.escape(c["reason"])}</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if st.button("去处理 →", key=f"go_{c['id']}", use_container_width=False):
                st.session_state['current_page'] = "客户工作台"
                st.session_state['ws_selected_id'] = c['id']
                st.rerun()
    else:
        st.success("🎉 今天没有待处理的客户，干得漂亮！")

    # =========================================================
    # 5. ⚡ 次优先
    # =========================================================
    if secondary_list:
        st.markdown('<div style="height:0.4rem;"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-header">'
            f'<span style="font-size:1.2rem;">⚡</span>'
            f'<span class="title">次优先</span>'
            f'<span class="badge" style="background:#f8fafc;color:#64748b;">{len(secondary_list)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for c in secondary_list:
            follow_display = c['follow_up_date'] if c['follow_up_date'] else '—'
            flag = _flag(c['country'])

            st.markdown(
                f'<div class="secondary-row">'
                f'<div class="left">'
                f'<span class="name">{html.escape(c["name"][:45])}</span>'
                f'<span class="meta">{flag} {html.escape(c["country"][:12])}</span>'
                f'<span class="tag grade-{c["grade_raw"].lower()}" style="font-size:0.65rem;">{html.escape(c["grade"])}</span>'
                f'<span class="meta">跟进 {follow_display}</span>'
                f'</div>'
                f'<div class="right">{html.escape(c["reason"])}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if st.button("去看看", key=f"sec_{c['id']}", use_container_width=False):
                st.session_state['current_page'] = "客户工作台"
                st.session_state['ws_selected_id'] = c['id']
                st.rerun()

    st.markdown("---")
    st.markdown(
        '<span style="color:#94a3b8;font-size:0.78rem;">'
        '去「客户工作台」查看全部客户 · 去「设置」管理团队和备份数据</span>',
        unsafe_allow_html=True,
    )
