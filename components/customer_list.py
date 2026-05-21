import streamlit as st
import pandas as pd
import html
from datetime import date
from database.db import Database

db = Database()

# ── 国家 → 国旗 ──
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


def render_customer_list(df, selected_id, page):
    """渲染左侧客户列表"""
    if df.empty:
        st.info("暂无客户")
        return

    page_size = 10
    total_items = len(df)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    if page >= total_pages:
        page = 0
        st.session_state['ws_page'] = 0

    start = page * page_size
    end = min(start + page_size, total_items)
    page_df = df.iloc[start:end]

    batch_ids = set(st.session_state.get('ws_batch_ids', []))
    batch_mode = st.session_state.get('ws_batch_mode', False)
    today = date.today()

    # ── 批量计数 ──
    if batch_mode and batch_ids:
        st.markdown(f'<span style="color:#1677FF;font-size:0.85rem;">已选 <strong>{len(batch_ids)}</strong> 个客户</span>', unsafe_allow_html=True)

    # ── 批量操作栏 ──
    if batch_mode and batch_ids:
        _render_batch_bar(batch_ids)

    # ── 客户卡片 ──
    for _, row in page_df.iterrows():
        cid = row['id']
        name = html.escape(str(row['company_name'])[:32])
        country = str(row.get('country', '') or '')[:15]
        flag = _flag(country)
        grade = str(row.get('customer_grade', 'C'))
        grade_tag = html.escape(f"{grade}级" if grade in ('A', 'B', 'C') else grade)
        dev_status = str(row.get('development_status', ''))
        event_count = int(row.get('event_count', 0))

        # 跟进日期
        fud = row.get('follow_up_date')
        follow_str = ''
        date_class = ''
        if pd.notna(fud) if not isinstance(fud, bool) else False:
            try:
                fd = pd.to_datetime(fud).date()
                days = (today - fd).days
                if days > 0:
                    follow_str = f'<span class="over">逾期 {days} 天</span>'
                elif days == 0:
                    follow_str = '<span class="due">今日跟进</span>'
                else:
                    follow_str = f'下次跟进 {fd.isoformat()}'
            except Exception:
                follow_str = f'下次跟进 {fud}'

        is_selected = (selected_id == cid)
        card_class = "ws-card-selected" if is_selected else "ws-card"

        # 卡片主体 HTML
        card_html = (
            f'<div class="{card_class}">'
            f'<div class="ws-card-top">'
            f'<span class="ws-card-name">{html.escape(name)}</span>'
            f'<span class="ws-card-flag">{flag} {html.escape(country)}</span>'
            f'</div>'
            f'<div class="ws-card-meta">'
            f'<span class="grade-{grade.lower()}">{grade_tag}</span>'
            f'<span class="dev-status">{html.escape(dev_status)}</span>'
            f'<span class="ws-card-count">{event_count} 次跟进</span>'
            f'</div>'
            f'<div class="ws-card-date">{follow_str}</div>'
            f'</div>'
        )

        if batch_mode:
            # In batch mode: checkbox + card + view button
            is_batched = cid in batch_ids
            cb_col, card_col = st.columns([0.08, 0.92])
            with cb_col:
                checked = st.checkbox("", value=is_batched, key=f"batch_{cid}", label_visibility="collapsed")
                if checked != is_batched:
                    batch_ids.add(cid) if checked else batch_ids.discard(cid)
                    st.session_state['ws_batch_ids'] = batch_ids
                    st.rerun()
            with card_col:
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button("→ 查看详情", key=f"sel_{cid}", help="查看客户详情"):
                    st.session_state['ws_selected_id'] = cid
                    for k in ['_followup_suggest', '_followup_grade', '_show_followup_datepicker']:
                        st.session_state.pop(k, None)
                    st.rerun()
        else:
            st.markdown(card_html, unsafe_allow_html=True)
            if st.button("→ 查看详情", key=f"sel_{cid}", help="查看客户详情"):
                st.session_state['ws_selected_id'] = cid
                for k in ['_followup_suggest', '_followup_grade', '_show_followup_datepicker']:
                    st.session_state.pop(k, None)
                st.rerun()

    st.session_state['ws_batch_ids'] = batch_ids

    # ── 分页 ──
    if total_pages > 1:
        pc1, pc2, pc3 = st.columns([1, 3, 1])
        with pc1:
            if st.button("◀ 上一页", disabled=(page == 0), use_container_width=True):
                st.session_state['ws_page'] = page - 1
                st.rerun()
        with pc2:
            st.markdown(f'<div class="pagination-text">{start + 1}-{end} / {total_items}</div>', unsafe_allow_html=True)
        with pc3:
            if st.button("下一页 ▶", disabled=(page >= total_pages - 1), use_container_width=True):
                st.session_state['ws_page'] = page + 1
                st.rerun()


def _render_batch_bar(batch_ids):
    st.markdown(
        f'<div style="background:#eef2ff;padding:0.5rem 0.8rem;border-radius:8px;'
        f'border:1px solid #c7d2fe;font-size:0.85rem;margin-bottom:6px;">'
        f'☑ 已选 <strong>{len(batch_ids)}</strong> 个，要做什么？</div>',
        unsafe_allow_html=True
    )

    bc1, bc2, bc3 = st.columns([1, 1, 1])
    with bc1:
        if st.button("改等级", use_container_width=True, key="batch_grade"):
            st.session_state['_batch_action'] = 'grade'
    with bc2:
        if st.button("改阶段", use_container_width=True, key="batch_stage"):
            st.session_state['_batch_action'] = 'stage'
    with bc3:
        if st.button("设跟进日", use_container_width=True, key="batch_follow"):
            st.session_state['_batch_action'] = 'followup'

    action = st.session_state.get('_batch_action')
    if action:
        with st.form("batch_action_form", clear_on_submit=True):
            if action == 'grade':
                target = st.selectbox("目标等级", ["A", "B", "C"])
                ca, cb = st.columns(2)
                with ca:
                    if st.form_submit_button("✓ 确认", type="primary"):
                        for cid in list(batch_ids):
                            db.update_customer(cid, {'customer_grade': target})
                        st.session_state['_batch_action'] = None
                        st.session_state['ws_batch_ids'] = set()
                        st.success(f"已改为 {target} 级")
                        st.rerun()
                with cb:
                    if st.form_submit_button("取消"):
                        st.session_state['_batch_action'] = None
                        st.rerun()
            elif action == 'stage':
                target = st.selectbox("目标阶段", ["初次开发", "已发开发信", "已报价", "样品阶段", "已成交"])
                ca, cb = st.columns(2)
                with ca:
                    if st.form_submit_button("✓ 确认", type="primary"):
                        for cid in list(batch_ids):
                            db.update_customer(cid, {'development_status': target})
                        st.session_state['_batch_action'] = None
                        st.session_state['ws_batch_ids'] = set()
                        st.success(f"已改为「{target}」")
                        st.rerun()
                with cb:
                    if st.form_submit_button("取消"):
                        st.session_state['_batch_action'] = None
                        st.rerun()
            elif action == 'followup':
                target = st.date_input("跟进日期", value=date.today())
                ca, cb = st.columns(2)
                with ca:
                    if st.form_submit_button("✓ 确认", type="primary"):
                        for cid in list(batch_ids):
                            db.update_customer(cid, {'follow_up_date': target.isoformat()})
                        st.session_state['_batch_action'] = None
                        st.session_state['ws_batch_ids'] = set()
                        st.success("已设置")
                        st.rerun()
                with cb:
                    if st.form_submit_button("取消"):
                        st.session_state['_batch_action'] = None
                        st.rerun()
