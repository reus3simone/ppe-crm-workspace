import streamlit as st
import pandas as pd
import html
from datetime import datetime, date
from database.db import Database

db = Database()


def render_workspace():
    st.title("👥 客户工作台")
    st.markdown("---")

    # ── 顶部操作栏 ──
    c1, c2, c3, c4 = st.columns([2, 1.5, 1, 1.2])
    with c1:
        search_key = st.text_input("🔍 搜索", placeholder="公司 / 联系人 / 邮箱 / 电话",
                                   label_visibility="collapsed")
    with c2:
        grade_filter = st.selectbox("等级", ["全部", "A", "B", "C"],
                                    label_visibility="collapsed")
    with c3:
        if st.button("➕ 新建", type="secondary", use_container_width=True):
            st.session_state['ws_new_customer'] = True
            st.rerun()
    with c4:
        if st.button("📥 批量导入", type="primary", use_container_width=True):
            st.session_state['ws_show_import'] = True
            st.rerun()

    # ── 导入弹窗 ──
    if st.session_state.get('ws_show_import', False):
        render_import_dialog()
        return

    # ── 新建客户 ──
    if st.session_state.get('ws_new_customer', False):
        render_new_customer_form()
        return

    # ── 编辑客户 ──
    edit_id = st.session_state.get('ws_edit_id')
    if edit_id:
        edit_customer, err = db.get_customer(edit_id)
        if edit_customer:
            render_edit_form(edit_customer)
            return

    # ── 加载数据 ──
    df, err = db.get_all_customers_with_stats()
    if err:
        st.error(f"数据加载失败：{err}")
        return

    # 搜索过滤
    if search_key:
        sk = search_key.lower()
        df = df[
            df['company_name'].str.contains(sk, case=False, na=False) |
            df['contact_person'].str.contains(sk, case=False, na=False) |
            df['email'].str.contains(sk, case=False, na=False) |
            df['phone'].str.contains(sk, case=False, na=False) |
            df['whatsapp'].str.contains(sk, case=False, na=False)
        ]
    if grade_filter != "全部":
        df = df[df['customer_grade'] == grade_filter]

    # ── 分栏布局：左列表 / 右详情 ──
    left_col, right_col = st.columns([0.38, 0.62])

    selected_id = st.session_state.get('ws_selected_id')

    # ===== 左：客户列表 =====
    with left_col:
        if df.empty:
            st.info("暂无客户")
            st.stop()

        # 紧凑列表
        for _, row in df.iterrows():
            cid = row['id']
            name = html.escape(str(row['company_name'])[:30])
            country = str(row.get('country', '') or '')[:12]
            grade = str(row.get('customer_grade', 'C'))
            grade_tag = f"{grade}级" if grade in ('A', 'B', 'C') else grade

            health = db.get_customer_health(row.get('last_follow_up_date'))
            event_count = int(row.get('event_count', 0))

            is_selected = (selected_id == cid)
            bg = "#eef2ff" if is_selected else "white"
            border = "2px solid #3b82f6" if is_selected else "1px solid #eef1f5"

            st.markdown(f"""
            <div style="background:{bg};padding:0.5rem 0.7rem;border-radius:6px;
                        border:{border};margin-bottom:3px;cursor:pointer;
                        display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-weight:600;font-size:0.85rem;color:#1e293b;">
                        {health['icon']} {name}
                    </span>
                    <span style="margin-left:4px;font-size:0.65rem;color:#64748b;">
                        {country}
                    </span>
                </div>
                <div style="display:flex;align-items:center;gap:4px;">
                    <span style="background:#e6f7ec;color:#15803d;padding:0 6px;
                              border-radius:8px;font-size:0.65rem;font-weight:600;">{grade_tag}</span>
                    <span style="font-size:0.65rem;color:#94a3b8;">{event_count}次</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("→", key=f"sel_{cid}", help="选择客户",
                         use_container_width=False):
                st.session_state['ws_selected_id'] = cid
                st.rerun()

    # ===== 右：客户详情 =====
    with right_col:
        if not selected_id:
            st.info("👈 请从左侧选择一个客户")
            st.stop()

        customer, err = db.get_customer(selected_id)
        if err or not customer:
            st.error("客户不存在")
            st.stop()

        render_customer_detail(customer)


def render_import_dialog():
    st.markdown("---")
    st.subheader("📥 Excel 批量导入")

    uploaded_file = st.file_uploader("上传 .xlsx / .xls 文件", type=['xlsx', 'xls'])
    if not uploaded_file:
        if st.button("✕ 关闭"):
            st.session_state['ws_show_import'] = False
            st.rerun()
        return

    # 用 ExcelFile 一次性读取，避免文件指针消耗
    try:
        xls = pd.ExcelFile(uploaded_file)
    except Exception as e:
        st.error(f"文件解析失败：{e}")
        return

    sheet_names = xls.sheet_names
    st.info(f"该文件包含 {len(sheet_names)} 个 sheet，请勾选要导入的：")

    # 默认排除关键词 sheet
    choices = {}
    for name in sheet_names:
        is_keyword = any(kw in name for kw in ['关键词', 'keyword', 'KEYWORD'])
        choices[name] = st.checkbox(name, value=not is_keyword)

    selected = [n for n, v in choices.items() if v]
    if not selected:
        st.warning("请至少勾选一个 sheet")
        return

    if st.button("✅ 开始导入", type="primary"):
        total_s, total_d, total_e = 0, 0, 0
        all_warnings = []
        progress = st.progress(0)
        status_text = st.empty()

        for i, sheet in enumerate(selected):
            status_text.info(f"正在导入：{sheet}...")
            s, d, e, warns, err = db.batch_import_sheet(xls, sheet)
            total_s += s
            total_d += d
            total_e += e
            all_warnings.extend(warns)
            progress.progress((i + 1) / len(selected))

        if all_warnings:
            for w in all_warnings:
                st.warning(w['message'])

        progress.empty()
        status_text.empty()
        st.success(f"✅ 导入完成｜成功：{total_s} ｜重复跳过：{total_d} ｜失败：{total_e}")

        if st.button("✕ 关闭"):
            st.session_state['ws_show_import'] = False
            st.rerun()


def render_new_customer_form():
    st.markdown("---")
    st.subheader("➕ 新建客户")

    with st.form("new_customer_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            company = st.text_input("公司名称 *")
            contact = st.text_input("联系人")
            email = st.text_input("邮箱")
            phone = st.text_input("电话")
            country = st.text_input("国家")
        with col2:
            grade = st.selectbox("客户等级", ["A", "B", "C"])
            status = st.selectbox("跟进状态", ["正在跟进", "备选", "拒绝"])
            source = st.text_input("客户来源", placeholder="Google / LinkedIn / 展会...")
            products = st.text_input("主营产品")
            website = st.text_input("官网")

        follow_up_date = st.date_input("下次跟进日期", value=datetime.now().date())
        notes = st.text_area("备注")
        submitted = st.form_submit_button("💾 保存", type="primary")

        if submitted:
            if not company.strip():
                st.error("公司名称为必填项")
                return
            data = {
                'company_name': company.strip(),
                'contact_person': contact,
                'email': email, 'phone': phone, 'country': country,
                'customer_grade': grade, 'status': status,
                'source': source, 'products': products,
                'website': website, 'notes': notes,
                'follow_up_date': follow_up_date.strftime('%Y-%m-%d'),
            }
            # 保护检查
            warns = db.check_protection_conflict(company, contact, email)
            if warns:
                for w in warns:
                    st.warning(w['message'])
                if not st.session_state.get('_confirm_protection'):
                    st.info("如果确认无冲突，请再次点击保存")
                    st.session_state['_confirm_protection'] = True
                    return

            cid, result = db.add_customer(data)
            if cid:
                st.success("新建成功")
                st.session_state['ws_new_customer'] = False
                st.session_state['_confirm_protection'] = False
                st.rerun()
            else:
                st.error(f"失败：{result}")

    if st.button("← 返回"):
        st.session_state['ws_new_customer'] = False
        st.rerun()


def render_customer_detail(customer):
    cid = customer['id']
    name = html.escape(str(customer['company_name']))
    grade = str(customer.get('customer_grade', 'C'))
    grade_tag = f"{grade}级" if grade in ('A', 'B', 'C') else grade

    # 顶部：客户名 + 等级 + 删除
    top_c1, top_c2 = st.columns([5, 1])
    with top_c1:
        health = db.get_customer_health(customer.get('last_follow_up_date'))
        st.markdown(f"### {health['icon']} {name}")
    with top_c2:
        if st.button("🗑 删除", type="primary", use_container_width=True):
            ok, err = db.delete_customer(cid)
            if ok:
                st.session_state['ws_selected_id'] = None
                st.success("已删除")
                st.rerun()
            else:
                st.error(f"删除失败：{err}")

    # 标签行
    status_str = str(customer.get('status', ''))
    dev_str = str(customer.get('development_status', ''))
    st.markdown(f"""
    <span style="background:#e6f7ec;color:#15803d;padding:0 8px;border-radius:8px;font-size:0.75rem;font-weight:600;">{grade_tag}</span>
    <span style="background:#eef2ff;color:#3b5fd9;padding:0 8px;border-radius:8px;font-size:0.75rem;font-weight:600;margin-left:4px;">{html.escape(status_str)}</span>
    <span style="background:#f8fafc;color:#64748b;padding:0 8px;border-radius:8px;font-size:0.75rem;margin-left:4px;">{html.escape(dev_str)}</span>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 三个 Tab
    tab1, tab2, tab3 = st.tabs(["📋 资料", "📅 跟进", "🔍 调研"])

    with tab1:
        render_info_tab(customer)

    with tab2:
        render_followup_tab(cid)

    with tab3:
        render_research_tab(customer)


def render_info_tab(customer):
    cid = customer['id']
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**基本信息**")
        rows = [
            ("联系人", customer.get('contact_person', '未填写')),
            ("邮箱", customer.get('email', '未填写')),
            ("电话", customer.get('phone', '未填写')),
            ("WhatsApp", customer.get('whatsapp', '未填写')),
            ("国家", customer.get('country', '未填写')),
        ]
        for label, val in rows:
            st.markdown(f"<div style='font-size:0.85rem;margin-bottom:4px;'>"
                        f"<span style='color:#64748b;'>{label}：</span>"
                        f"<span style='color:#1e293b;'>{html.escape(str(val))}</span></div>",
                        unsafe_allow_html=True)
        if customer.get('linkedin'):
            st.markdown(f"<a href='{customer['linkedin']}' target='_blank'>🔗 LinkedIn</a>",
                        unsafe_allow_html=True)
        if customer.get('website'):
            st.markdown(f"<a href='{customer['website']}' target='_blank'>🌐 官网</a>",
                        unsafe_allow_html=True)

    with col2:
        st.markdown("**业务信息**")
        rows2 = [
            ("来源", customer.get('source', '未填写')),
            ("开发阶段", customer.get('development_status', '未填写')),
            ("主营产品", customer.get('products', '未填写')),
        ]
        for label, val in rows2:
            st.markdown(f"<div style='font-size:0.85rem;margin-bottom:4px;'>"
                        f"<span style='color:#64748b;'>{label}：</span>"
                        f"<span style='color:#1e293b;'>{html.escape(str(val))}</span></div>",
                        unsafe_allow_html=True)
        fud = customer.get('follow_up_date', '')
        if fud:
            st.markdown(f"<div style='font-size:0.85rem;margin-bottom:4px;'>"
                        f"<span style='color:#64748b;'>下次跟进：</span>"
                        f"<span style='color:#1e293b;'>{fud}</span></div>",
                        unsafe_allow_html=True)

        # 样品信息
        sample = customer.get('sample_status', '未寄出')
        st.markdown(f"**样品**：{sample}")
        if sample != '未寄出' and customer.get('sample_tracking_number'):
            st.markdown(f"快递单号：{customer['sample_tracking_number']}")

    st.markdown("---")
    notes = customer.get('notes', '')
    st.markdown("**备注**")
    st.markdown(notes if notes else '暂无备注', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("✏️ 编辑资料", use_container_width=True):
        st.session_state['ws_edit_id'] = cid
        st.rerun()


def render_edit_form(customer):
    cid = customer['id']
    st.markdown("---")
    st.subheader("✏️ 修改资料")

    with st.form(f"edit_form_{cid}", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            company = st.text_input("公司名称", customer['company_name'])
            contact = st.text_input("联系人", customer.get('contact_person', ''))
            email = st.text_input("邮箱", customer.get('email', ''))
            phone = st.text_input("电话", customer.get('phone', ''))
            whatsapp = st.text_input("WhatsApp", customer.get('whatsapp', ''))
            country = st.text_input("国家", customer.get('country', ''))
        with col2:
            grade = st.selectbox("等级", ["A", "B", "C"],
                                 index=['A', 'B', 'C'].index(
                                     customer.get('customer_grade', 'C')
                                     if customer.get('customer_grade', 'C') in ['A', 'B', 'C'] else "C"))
            status = st.selectbox("跟进状态", ["正在跟进", "备选", "拒绝"],
                                  index=["正在跟进", "备选", "拒绝"].index(
                                      customer.get('status', '正在跟进')
                                      if customer.get('status', '') in ["正在跟进", "备选", "拒绝"] else "正在跟进"))
            dev_status = st.selectbox("开发阶段",
                                      ["初次开发", "已发开发信", "已报价", "样品阶段", "已成交"],
                                      index=["初次开发", "已发开发信", "已报价", "样品阶段", "已成交"].index(
                                          customer.get('development_status', '初次开发')
                                          if customer.get('development_status', '') in [
                                              "初次开发", "已发开发信", "已报价", "样品阶段", "已成交"] else "初次开发"))
            products = st.text_input("主营产品", customer.get('products', ''))
            website = st.text_input("官网", customer.get('website', ''))
            linkedin = st.text_input("LinkedIn", customer.get('linkedin', ''))
            source = st.text_input("来源", customer.get('source', ''))

        st.markdown("**跟进计划**")
        fc1, fc2 = st.columns(2)
        with fc1:
            follow_up_date = st.date_input("下次跟进日期",
                value=pd.to_datetime(customer['follow_up_date']).date()
                if customer.get('follow_up_date') else datetime.now().date())
        with fc2:
            st.caption("设定后首页会提醒你按时跟进")

        st.markdown("**样品信息**")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            sample_status = st.selectbox("样品状态", ["未寄出", "已寄出", "已收到", "已反馈"],
                                         index=["未寄出", "已寄出", "已收到", "已反馈"].index(
                                             customer.get('sample_status', '未寄出')
                                             if customer.get('sample_status', '') in [
                                                 "未寄出", "已寄出", "已收到", "已反馈"] else "未寄出"))
        with sc2:
            sample_date = st.text_input("寄出日期", customer.get('sample_send_date', ''))
        with sc3:
            tracking = st.text_input("快递单号", customer.get('sample_tracking_number', ''))
        sample_feedback = st.text_area("样品反馈", customer.get('sample_feedback', ''))

        notes = st.text_area("备注", customer.get('notes', ''))
        submitted = st.form_submit_button("💾 保存修改", type="primary")

        if submitted:
            data = {
                'company_name': company.strip(), 'contact_person': contact,
                'email': email, 'phone': phone, 'whatsapp': whatsapp,
                'country': country, 'customer_grade': grade,
                'status': status, 'development_status': dev_status,
                'products': products, 'website': website, 'linkedin': linkedin,
                'source': source,
                'follow_up_date': follow_up_date.strftime('%Y-%m-%d'),
                'sample_status': sample_status,
                'sample_send_date': sample_date,
                'sample_tracking_number': tracking,
                'sample_feedback': sample_feedback,
                'notes': notes,
            }
            ok, result = db.update_customer(cid, data)
            if ok:
                st.success("修改成功")
                st.session_state['ws_edit_id'] = None
                st.rerun()
            else:
                st.error(f"失败：{result}")

    if st.button("← 取消修改"):
        st.session_state['ws_edit_id'] = None
        st.rerun()


def render_followup_tab(cid):
    st.markdown("**跟进时间轴**")

    # 写跟进
    with st.expander("✏️ 写跟进记录", expanded=False):
        with st.form(f"followup_form_{cid}", clear_on_submit=True):
            event_type = st.selectbox("事件类型", ["跟进邮件", "电话沟通", "WhatsApp", "客户回复", "样品沟通", "其他"])
            content = st.text_area("内容", placeholder="记录这次跟进...", height=100)
            submitted = st.form_submit_button("💾 保存跟进", type="primary")
            if submitted and content.strip():
                ok, _ = db.add_timeline_event(cid, event_type, content.strip())
                if ok:
                    st.success("已记录")
                    st.rerun()

    # 时间轴
    tl_df, _ = db.get_customer_timeline(cid)
    if tl_df.empty:
        st.info("暂无跟进记录")
        return

    for _, e in tl_df.iterrows():
        st.markdown(f"""
        <div style="padding-left:1.2rem;border-left:2px solid #cbd5e1;margin-bottom:1rem;position:relative;">
            <div style="position:absolute;left:-0.4rem;top:0.2rem;width:0.7rem;height:0.7rem;
                        border-radius:50%;background:#3b82f6;border:2px solid white;"></div>
            <div style="font-size:0.7rem;color:#94a3b8;">{e['created_at']}</div>
            <div style="font-weight:600;font-size:0.8rem;color:#3b82f6;">{e['event_type']}</div>
            <div style="font-size:0.85rem;color:#1e293b;">{e['event_content']}</div>
        </div>
        """, unsafe_allow_html=True)


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
        st.markdown("---")
        st.subheader("🤝 商务礼仪建议")
        st.markdown(f"""
**工作日**：{culture['weekend']}
**最佳发送日**：{culture['best_days']}
**避开**：{culture['avoid_days']}
**商务语言**：{culture['language']}
        """)
        with st.expander("📌 礼仪细节"):
            for tip in culture['etiquette']:
                st.markdown(f"- {tip}")
        with st.expander("⚠️ 禁忌提示"):
            for taboo in culture['taboos']:
                st.markdown(f"- {taboo}")
        if culture.get('holidays'):
            st.markdown(f"**近期节日**：{culture['holidays']}")
    else:
        st.markdown("---")
        st.caption("（未收录该国家的商务礼仪，后续可补充）")

    st.markdown("---")

    # 产品匹配
    st.subheader("🔗 产品匹配")
    matches = db.get_product_match(
        customer.get('industry', ''),
        customer.get('products', ''),
        customer.get('notes', '')
    )
    if matches:
        for m in matches:
            icon = "⭐" if m['priority'] == '⭐ 优先' else "📌"
            st.markdown(f"{icon} **{m['product']}** — {m['priority']}")
    else:
        st.markdown("暂未匹配到产品线，完善客户信息后自动匹配")

    st.markdown("---")

    # 调研笔记
    st.subheader("📝 调研笔记")
    notes_key = f"research_notes_{cid}"
    saved_notes = st.session_state.get(notes_key, customer.get('notes', ''))

    new_notes = st.text_area("调研发现", value=saved_notes, height=150,
                             key=f"r_notes_{cid}",
                             label_visibility="collapsed")

    if st.button("💾 保存笔记", type="primary", key=f"save_notes_{cid}"):
        ok, _ = db.update_customer(cid, {'notes': new_notes})
        if ok:
            db.add_timeline_event(cid, "背调完成", "调研笔记已更新")
            st.success("已保存")
            st.rerun()
