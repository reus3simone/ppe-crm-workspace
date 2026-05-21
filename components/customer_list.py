import streamlit as st
import pandas as pd
import html
from datetime import date
from database.db import Database

db = Database()


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

    # ── 批量切换 + 计数 ──
    bar_c1, bar_c2 = st.columns([1, 4])
    with bar_c1:
        if batch_mode:
            if st.button("✕ 退出批量", use_container_width=True):
                st.session_state['ws_batch_mode'] = False
                st.session_state['ws_batch_ids'] = set()
                st.session_state['_batch_action'] = None
                st.rerun()
        else:
            if st.button("☑ 批量", use_container_width=True):
                st.session_state['ws_batch_mode'] = True
                st.rerun()
    with bar_c2:
        if batch_mode and batch_ids:
            st.markdown(f'<span style="color:#4f8fff;font-size:0.85rem;">已选 <strong>{len(batch_ids)}</strong> 个客户</span>', unsafe_allow_html=True)

    # ── 批量操作栏 ──
    if batch_mode and batch_ids:
        _render_batch_bar(batch_ids)

    # ── 客户卡片 ──
    for _, row in page_df.iterrows():
        cid = row['id']
        name = html.escape(str(row['company_name'])[:30])
        country = html.escape(str(row.get('country', '') or '')[:12])
        grade = str(row.get('customer_grade', 'C'))
        grade_tag = html.escape(f"{grade}级" if grade in ('A', 'B', 'C') else grade)
        health = db.get_customer_health(row.get('last_follow_up_date'))
        event_count = int(row.get('event_count', 0))

        is_overdue = False
        fud = row.get('follow_up_date')
        if pd.notna(fud) if not isinstance(fud, bool) else False:
            try:
                is_overdue = (today - pd.to_datetime(fud).date()).days > 0
            except Exception:
                pass

        is_selected = (selected_id == cid)
        card_class = "ws-card-selected" if is_selected else "ws-card"
        overdue_mark = '<span style="color:#ef4444;font-size:0.65rem;margin-left:4px;">⚠</span>' if is_overdue else ''

        if batch_mode:
            # 批量模式：紧凑三列
            bcols = st.columns([0.07, 0.73, 0.20])
            with bcols[0]:
                is_batched = cid in batch_ids
                lbl = "✓" if is_batched else "○"
                if st.button(lbl, key=f"bt_{cid}",
                             type="primary" if is_batched else "secondary"):
                    batch_ids.add(cid) if not is_batched else batch_ids.discard(cid)
                    st.session_state['ws_batch_ids'] = batch_ids
                    st.rerun()
            with bcols[1]:
                st.markdown(
                    f'<div class="{card_class}">'
                    f'<div><span class="ws-card-name">{health["icon"]} {name}{overdue_mark}</span>'
                    f'<span class="ws-card-country">{country}</span></div>'
                    f'<div style="display:flex;align-items:center;gap:6px;">'
                    f'<span class="grade-{grade.lower()}">{grade_tag}</span>'
                    f'<span class="ws-card-count">{event_count}次</span></div></div>',
                    unsafe_allow_html=True
                )
            with bcols[2]:
                if st.button("→ 详情", key=f"sel_{cid}"):
                    st.session_state['ws_selected_id'] = cid
                    for k in ['_followup_suggest', '_followup_grade', '_show_followup_datepicker']:
                        st.session_state.pop(k, None)
                    st.rerun()
        else:
            # 普通模式：全宽卡片
            st.markdown(
                f'<div class="{card_class}">'
                f'<div><span class="ws-card-name">{health["icon"]} {name}{overdue_mark}</span>'
                f'<span class="ws-card-country">{country}</span></div>'
                f'<div style="display:flex;align-items:center;gap:6px;">'
                f'<span class="grade-{grade.lower()}">{grade_tag}</span>'
                f'<span class="ws-card-count">{event_count}次</span></div></div>',
                unsafe_allow_html=True
            )
            if st.button("查看 →", key=f"sel_{cid}", help="查看详情"):
                st.session_state['ws_selected_id'] = cid
                for k in ['_followup_suggest', '_followup_grade', '_show_followup_datepicker']:
                    st.session_state.pop(k, None)
                st.rerun()

    st.session_state['ws_batch_ids'] = batch_ids

    # ── 分页控件 ──
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
