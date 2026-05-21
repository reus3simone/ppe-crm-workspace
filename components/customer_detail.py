import streamlit as st
import html
from datetime import datetime, date, timedelta
from database.db import Database

db = Database()


def render_customer_detail(customer):
    cid = customer['id']
    name = html.escape(str(customer['company_name']))
    grade = str(customer.get('customer_grade', 'C'))
    grade_tag = f"{grade}级" if grade in ('A', 'B', 'C') else grade

    top_c1, top_c2 = st.columns([5, 1])
    with top_c1:
        health = db.get_customer_health(customer.get('last_follow_up_date'))
        st.markdown(f"### {health['icon']} {name}")
    with top_c2:
        if st.button("🗑 删除", type="primary", use_container_width=True):
            ok, err = db.delete_customer(cid)
            if ok:
                st.session_state['ws_selected_id'] = None
                for k in ['_followup_suggest', '_followup_grade', '_show_followup_datepicker']:
                    st.session_state.pop(k, None)
                st.success("已删除")
                st.rerun()
            else:
                st.error(f"删除失败：{err}")

    status_str = str(customer.get('status', ''))
    dev_str = str(customer.get('development_status', ''))
    st.markdown(f"""<span class="grade-{grade.lower()}">{grade_tag}</span><span class="status-active">{html.escape(status_str)}</span><span style="background:#f8fafc;color:#64748b;padding:2px 10px;border-radius:12px;font-size:0.75rem;margin-left:6px;">{html.escape(dev_str)}</span>""", unsafe_allow_html=True)

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📋 资料", "📅 跟进", "🔍 调研"])

    with tab1:
        render_info_tab(customer)

    with tab2:
        render_followup_tab(cid, customer)

    with tab3:
        render_research_tab(customer)


def render_info_tab(customer):
    cid = customer['id']
    _b = '<span style="color:#94a3b8;">未填写</span>'

    def _v(val):
        return html.escape(str(val)) if val else _b

    contact = _v(customer.get('contact_person'))
    email = _v(customer.get('email'))
    phone = _v(customer.get('phone'))
    whatsapp = _v(customer.get('whatsapp'))
    country = _v(customer.get('country'))
    source = _v(customer.get('source'))
    dev_s = _v(customer.get('development_status'))
    products = _v(customer.get('products'))

    fud = customer.get('follow_up_date', '')
    follow_up = f'<span class="info-value">{fud}</span>' if fud else _b

    sample = customer.get('sample_status', '未寄出')
    tracking = customer.get('sample_tracking_number', '')
    sample_rows = f'<div class="info-row"><span class="info-label">样品</span><span class="info-value">{sample}</span></div>'
    if sample != '未寄出' and tracking:
        sample_rows += f'<div class="info-row"><span class="info-label">快递单号</span><span class="info-value">{html.escape(tracking)}</span></div>'

    links = ''
    if customer.get('linkedin'):
        links += f'<a href="{customer["linkedin"]}" target="_blank" style="color:#4f8fff;text-decoration:none;font-size:0.85rem;margin-right:12px;">🔗 LinkedIn</a>'
    if customer.get('website'):
        links += f'<a href="{customer["website"]}" target="_blank" style="color:#4f8fff;text-decoration:none;font-size:0.85rem;">🌐 官网</a>'

    st.markdown(
        f'<div class="detail-section"><div style="display:grid;grid-template-columns:1fr 1fr;gap:0 2rem;">'
        f'<div><h5>基本信息</h5>'
        f'<div class="info-row"><span class="info-label">联系人</span><span class="info-value">{contact}</span></div>'
        f'<div class="info-row"><span class="info-label">邮箱</span><span class="info-value">{email}</span></div>'
        f'<div class="info-row"><span class="info-label">电话</span><span class="info-value">{phone}</span></div>'
        f'<div class="info-row"><span class="info-label">WhatsApp</span><span class="info-value">{whatsapp}</span></div>'
        f'<div class="info-row"><span class="info-label">国家</span><span class="info-value">{country}</span></div>'
        f'{links}'
        f'</div><div><h5>业务信息</h5>'
        f'<div class="info-row"><span class="info-label">来源</span><span class="info-value">{source}</span></div>'
        f'<div class="info-row"><span class="info-label">开发阶段</span><span class="info-value">{dev_s}</span></div>'
        f'<div class="info-row"><span class="info-label">主营产品</span><span class="info-value">{products}</span></div>'
        f'<div class="info-row"><span class="info-label">下次跟进</span><span class="info-value">{follow_up}</span></div>'
        f'{sample_rows}'
        f'</div></div></div>',
        unsafe_allow_html=True
    )

    notes = customer.get('notes', '')
    notes_display = html.escape(notes) if notes else '<span style="color:#94a3b8;">暂无备注</span>'
    st.markdown(
        f'<div class="detail-section"><h5>备注</h5>'
        f'<div style="font-size:0.85rem;color:#1e293b;line-height:1.6;min-height:2rem;">{notes_display}</div></div>',
        unsafe_allow_html=True
    )

    if st.button("✏️ 编辑资料", use_container_width=True):
        st.session_state['ws_edit_id'] = cid
        st.rerun()


def render_followup_tab(cid, customer=None):
    st.markdown("##### 跟进时间轴")

    # 写跟进
    with st.expander("✏️ 写跟进记录", expanded=False):
        with st.form(f"followup_form_{cid}", clear_on_submit=True):
            event_type = st.selectbox("事件类型", ["跟进邮件", "电话沟通", "WhatsApp", "客户回复", "样品沟通", "其他"])
            content = st.text_area("内容", placeholder="记录这次跟进...", height=100)
            submitted = st.form_submit_button("💾 保存跟进", type="primary")
            if submitted and content.strip():
                ok, _ = db.add_timeline_event(cid, event_type, content.strip())
                if ok:
                    # 跟进闭环：根据等级算建议下次跟进日
                    if customer is None:
                        c, _ = db.get_customer(cid)
                    else:
                        c = customer
                    grade = c.get('customer_grade', 'B') if c else 'B'
                    delta_days = {'A': 3, 'B': 7, 'C': 14}.get(grade, 7)
                    suggested = (date.today() + timedelta(days=delta_days)).isoformat()
                    st.session_state['_followup_suggest'] = suggested
                    st.session_state['_followup_grade'] = grade
                    st.success("已记录")
                    st.rerun()

    # ── 跟进闭环建议 ──
    _show_suggest(st.session_state.get('_followup_suggest'), cid)

    # 时间轴
    tl_df, _ = db.get_customer_timeline(cid)
    if tl_df.empty:
        st.info("暂无跟进记录")
        return

    for _, e in tl_df.iterrows():
        st.markdown(f"""<div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-date">{html.escape(str(e['created_at']))}</div><div class="timeline-content"><strong style="color:#3b82f6;font-size:0.8rem;">{html.escape(str(e['event_type']))}</strong><div style="font-size:0.85rem;color:#1e293b;margin-top:2px;">{html.escape(str(e['event_content']))}</div></div></div>""", unsafe_allow_html=True)


def _show_suggest(suggest_date, cid):
    if not suggest_date:
        return
    grade = st.session_state.get('_followup_grade', 'B')
    st.markdown(f"""<div style="background:#eef2ff;padding:0.8rem 1rem;border-radius:8px;border:1px solid #c7d2fe;font-size:0.85rem;margin-bottom:1rem;"><strong>📅 跟进闭环</strong><br><span style="color:#1e293b;">根据 {grade} 级客户跟进策略，建议下次跟进日期为：<strong>{suggest_date}</strong></span></div>""", unsafe_allow_html=True)

    ca, cb, cc = st.columns([1, 1, 1])
    with ca:
        if st.button("✓ 确认此日期", use_container_width=True, key="fs_confirm"):
            db.update_customer(cid, {'follow_up_date': suggest_date})
            _clear_suggest()
            st.success("已更新下次跟进日期")
            st.rerun()
    with cb:
        if st.button("✏️ 改日期", use_container_width=True, key="fs_edit"):
            st.session_state['_show_followup_datepicker'] = True
    with cc:
        if st.button("跳过", use_container_width=True, key="fs_skip"):
            _clear_suggest()
            st.rerun()

    if st.session_state.get('_show_followup_datepicker'):
        new_date = st.date_input("选择日期", key="fs_datepicker")
        if st.button("确认日期", key="fs_save_date"):
            db.update_customer(cid, {'follow_up_date': new_date.isoformat()})
            _clear_suggest()
            st.success("已更新下次跟进日期")
            st.rerun()


def _clear_suggest():
    for k in ['_followup_suggest', '_followup_grade', '_show_followup_datepicker']:
        st.session_state.pop(k, None)


def render_research_tab(customer):
    cid = customer['id']

    # 时区
    st.subheader("🕐 时区建议")
    tz = db.get_timezone_advice(customer.get('country', ''))
    if tz:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d %H:%M")
        st.markdown(f"""
<div style="background:#f8fafc;padding:0.8rem 1rem;border-radius:8px;border:1px solid #eef1f5;font-size:0.85rem;line-height:1.7;">
    <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
        <span><strong>🖥 本机时间</strong>：{date_str}（北京时间）</span>
        <span style="color:#64748b;">⏱ 仅供参考，以实际为准</span>
    </div>
    <hr style="margin:6px 0;border:none;border-top:1px solid #eef1f5;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 16px;">
        <span><strong>📍 客户所在地</strong>：{tz['label']}（UTC{tz['utc']:+g}）</span>
        <span><strong>🕒 客户当地时间</strong>：{tz['local_now']}</span>
        <span><strong>📮 最佳发送窗口</strong>：{tz['local_window']}（客户当地）</span>
        <span><strong>🇨🇳 对应北京时间</strong>：<strong>{tz['cst_range']}</strong></span>
    </div>
    <div style="margin-top:4px;color:#64748b;font-size:0.8rem;">{tz['dst_text']}</div>
</div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("填写国家后自动识别时区")

    # 商务礼仪
    culture = db.get_cultural_advice(customer.get('country', ''))
    if culture:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**工作日**：{culture['weekend']}")
            st.markdown(f"**最佳发送日**：{culture['best_days']}")
        with col_b:
            st.markdown(f"**避开**：{culture['avoid_days']}")
            st.markdown(f"**商务语言**：{culture['language']}")
        with st.expander("📌 礼仪细节"):
            for tip in culture['etiquette']:
                st.markdown(f"- {tip}")
        with st.expander("⚠️ 禁忌提示"):
            for taboo in culture['taboos']:
                st.markdown(f"- {taboo}")
        if culture.get('holidays'):
            st.markdown(f"**近期节日**：{culture['holidays']}")
    else:
        st.caption("（未收录该国家的商务礼仪，后续可补充）")

    # 产品匹配
    matches = db.get_product_match(
        customer.get('industry', ''),
        customer.get('products', ''),
        customer.get('notes', '')
    )
    if matches:
        match_html = ''
        for m in matches:
            icon = "⭐" if m['priority'] == '⭐ 优先' else "📌"
            match_html += f'<div style="padding:4px 0;"><span style="font-size:1rem;">{icon}</span> <strong>{html.escape(m["product"])}</strong> <span style="color:#64748b;font-size:0.85rem;">— {m["priority"]}</span></div>'
        st.markdown(f'<div class="detail-section"><h5>🔗 产品匹配</h5>{match_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="detail-section"><h5>🔗 产品匹配</h5><span style="color:#94a3b8;font-size:0.85rem;">暂未匹配到产品线，完善客户信息后自动匹配</span></div>', unsafe_allow_html=True)

    # 调研笔记
    st.markdown(f'<div class="detail-section"><h5>📝 调研笔记</h5></div>', unsafe_allow_html=True)
    notes_key = f"research_notes_{cid}"
    saved_notes = st.session_state.get(notes_key, customer.get('notes', ''))

    new_notes = st.text_area("调研发现", value=saved_notes, height=150,
                             key=f"r_notes_{cid}",
                             label_visibility="collapsed")

    if st.button("💾 保存笔记", key=f"save_notes_{cid}"):
        ok, _ = db.update_customer(cid, {'notes': new_notes})
        if ok:
            db.add_timeline_event(cid, "背调完成", "调研笔记已更新")
            st.success("已保存")
            st.rerun()
