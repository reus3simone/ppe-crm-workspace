
import streamlit as st
import pandas as pd
import html
from datetime import datetime
from database.db import Database

db = Database()

def render_customer_list():
    st.title("👥 客户全量管理")
    st.markdown("---")

    # 处理首页跳转的筛选
    home_filter = st.session_state.pop('home_filter', None)

    # 视图切换
    view_mode = st.radio("", ["📋 列表视图", "📊 看板视图"],
                         horizontal=True, label_visibility="collapsed")

    # 筛选栏
    with st.container():
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
        with c1:
            search_key = st.text_input("🔍 搜索公司名/邮箱")
        with c2:
            if home_filter and home_filter.startswith('grade_'):
                default_grade = home_filter.split('_')[1]
                grade_filter = st.selectbox("客户等级", ["全部", "A", "B", "C"],
                    index=["全部","A","B","C"].index(default_grade))
            else:
                grade_filter = st.selectbox("客户等级", ["全部", "A", "B", "C"])
        with c3:
            dev_status_options = ["全部", "初次开发", "已发开发信", "已报价", "样品阶段"]
            if home_filter in ('pending', 'quoted', 'sample'):
                dev_map_idx = {'pending': 1, 'quoted': 2, 'sample': 3}
                dev_filter = st.selectbox("开发状态", dev_status_options, index=dev_map_idx[home_filter])
            else:
                dev_filter = st.selectbox("开发状态", dev_status_options)
        with c4:
            status_filter = st.selectbox("跟进状态", ["全部", "正在跟进", "备选", "拒绝"])
        with c5:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📥 批量导入", type="primary", use_container_width=True):
                st.session_state['show_import'] = True
                st.rerun()

    # 批量导入弹窗
    if st.session_state.get('show_import', False):
        with st.expander("📥 Excel批量导入客户", expanded=True):
            st.info("""
            **支持两种格式：**
            - **客户跟进表格式**：公司、国家、公司定位、业务对接、联系方式、开发进度、客户意向、备注（自动解析邮箱/电话/联系人）
            - **通用格式**：company_name、contact_person、email、phone、country、linkedin、website、products、notes、customer_grade
            """)
            uploaded_file = st.file_uploader("上传.xlsx/.xls文件", type=['xlsx', 'xls'])
            if uploaded_file:
                try:
                    df = pd.read_excel(uploaded_file)
                    st.write(f"读取到 {len(df)} 条数据，预览前5行：")
                    st.dataframe(df.head(), use_container_width=True)
                    if st.button("✅ 确认导入", type="primary"):
                        s, d, e, err = db.batch_import_customers(df)
                        if err:
                            st.error(f"导入失败：{err}")
                        else:
                            st.success(f"导入完成｜成功：{s} ｜重复：{d} ｜失败：{e}")
                            st.session_state['show_import'] = False
                            st.rerun()
                except Exception as ex:
                    st.error(f"文件解析失败：{str(ex)}")
            if st.button("取消关闭"):
                st.session_state['show_import'] = False
                st.rerun()

    # 客户列表加载与筛选（附带跟进统计）
    df, err = db.get_all_customers_with_stats()
    if err:
        st.error(f"数据加载失败：{err}")
        return

    # 搜索筛选
    if search_key:
        df = df[
            df['company_name'].str.contains(search_key, case=False, na=False) |
            df['email'].str.contains(search_key, case=False, na=False)
        ]
    if grade_filter != "全部":
        df = df[df['customer_grade'] == grade_filter]
    if status_filter != "全部":
        df = df[df['status'] == status_filter]
    if dev_filter != "全部":
        df = df[df['development_status'] == dev_filter]

    # 首页"今日待跟进"筛选
    if home_filter == 'followup':
        today = datetime.now().date()
        def _is_due(fud):
            if not fud or pd.isna(fud):
                return False
            try:
                return pd.to_datetime(fud).date() <= today
            except Exception:
                return False
        df = df[df['follow_up_date'].apply(_is_due)]

    today = datetime.now().date()

    # 计算每个客户的健康度和跟进统计
    def _calc_health(row):
        return db.get_customer_health(row.get('last_follow_up_date'))

    def _calc_next_action(row):
        cid = row['id']
        d, msg = db.calculate_next_follow_up(cid)
        if d:
            days = (d - today).days
            return d, msg, days
        return None, msg, None

    if view_mode == "📋 列表视图":
        # ===== 列表视图（增强版）=====
        st.markdown("---")
        if st.button("➕ 新建客户档案", type="primary"):
            st.session_state['show_add_form'] = True
            st.rerun()
        st.markdown("---")

        if df.empty:
            st.info("暂无匹配的客户数据")
            return

        for _, row in df.iterrows():
            company_name = html.escape(str(row['company_name']))
            country_show = html.escape(str(row['country'])) if pd.notna(row['country']) else "未知国家"
            contact_show = html.escape(str(row['contact_person'])) if pd.notna(row['contact_person']) else "暂无联系人"
            email_show = html.escape(str(row['email'])) if pd.notna(row['email']) else "暂无邮箱"
            phone_show = html.escape(str(row['whatsapp'])) if pd.notna(row['whatsapp']) else (html.escape(str(row['phone'])) if pd.notna(row['phone']) else "暂无电话")

            # 健康度
            health = _calc_health(row)
            # 跟进次数
            event_count = int(row.get('event_count', 0))
            # 下次跟进
            next_date, next_msg, days_left = _calc_next_action(row)
            next_str = ""
            if next_date:
                if days_left is not None and days_left <= 0:
                    next_str = f'<span style="color:#ef4444;font-size:0.75rem;">📅 已到期</span>'
                elif days_left is not None:
                    next_str = f'<span style="color:#64748b;font-size:0.75rem;">📅 {next_date.strftime("%m/%d")}（{days_left}天后）</span>'

            linkedin_html = ""
            if pd.notna(row['linkedin']) and str(row['linkedin']).strip():
                linkedin_html = f'<a href="{html.escape(str(row["linkedin"]))}" target="_blank" style="margin-left:8px;">🔗 LinkedIn</a>'

            # 逾期标记
            overdue_html = ""
            fud = row.get('follow_up_date')
            if fud and pd.notna(fud):
                try:
                    fud_date = pd.to_datetime(fud).date()
                    if fud_date < today:
                        days = (today - fud_date).days
                        overdue_html = f'<span style="background:#fef2f2;color:#dc2626;padding:2px 8px;border-radius:10px;font-size:0.7rem;font-weight:600;margin-left:6px;">⚠ 逾期{days}天</span>'
                    elif fud_date == today:
                        overdue_html = f'<span style="background:#fef9e7;color:#b45309;padding:2px 8px;border-radius:10px;font-size:0.7rem;font-weight:600;margin-left:6px;">📅 今日</span>'
                except Exception:
                    pass

            grade = str(row['customer_grade'])
            grade_display = f"{grade}级" if grade in ('A', 'B', 'C') else html.escape(grade)
            grade_css = f"grade-{grade.lower()}" if grade.lower() in ('a', 'b', 'c') else "grade-c"

            st.markdown(f"""
            <div class="customer-card">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h4 style="margin:0;">
                            {health['icon']} {company_name}{overdue_html}
                        </h4>
                        <div style="margin-top:6px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                            <span class="{grade_css}">{grade_display}</span>
                            <span class="status-{"active" if row["status"] == "正在跟进" else "pending" if row["status"] == "备选" else "rejected"}">{html.escape(str(row['status']))}</span>
                            <span style="font-size:0.75rem;color:#64748b;">跟进{event_count}次</span>
                            <span style="font-size:0.75rem;color:#64748b;">{health['label']}</span>
                            {next_str}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:12px; color:#64748b;">{country_show}</div>
                        {linkedin_html}
                    </div>
                </div>
                <div style="margin-top:8px; font-size:14px; color:#475569;">
                    {contact_show}｜{email_show}｜{phone_show}
                </div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
            with c1:
                if st.button("查看详情", key=f"v_{row['id']}"):
                    st.session_state['selected_customer'] = row['id']
                    st.rerun()
            with c2:
                if st.button("编辑", key=f"e_{row['id']}"):
                    st.session_state['edit_customer'] = row['id']
                    st.rerun()
            with c3:
                if st.button("删除", key=f"d_{row['id']}", type="primary"):
                    ok, err = db.delete_customer(row['id'])
                    if ok:
                        st.success("删除成功")
                    else:
                        st.error(f"删除失败：{err}")
                    st.rerun()

    else:
        # ===== 看板视图（Pipeline）=====
        st.markdown("---")
        st.caption("💡 点击卡片上的「推进」按钮将客户移至下一阶段")

        if df.empty:
            st.info("暂无匹配的客户数据")
            return

        stages = ["初次开发", "已报价", "样品阶段", "已成交"]
        stage_colors = ["#eef2ff", "#fef9e7", "#e6f7ec", "#ede9fe"]
        cols = st.columns(len(stages))

        for i, stage in enumerate(stages):
            with cols[i]:
                stage_df = df[df['development_status'] == stage]
                count = len(stage_df)
                st.markdown(f"""
                <div style="background:{stage_colors[i]};padding:8px 12px;border-radius:8px;
                            text-align:center;margin-bottom:12px;">
                    <span style="font-weight:700;font-size:1rem;">{stage}</span>
                    <span style="font-size:0.8rem;color:#64748b;margin-left:6px;">{count}</span>
                </div>
                """, unsafe_allow_html=True)

                if stage == "已成交":
                    for _, row in stage_df.iterrows():
                        health = _calc_health(row)
                        cname = html.escape(str(row['company_name']))
                        grade = str(row['customer_grade'])
                        gd = f"{grade}级" if grade in ('A', 'B', 'C') else grade
                        st.markdown(f"""
                        <div class="customer-card" style="padding:0.6rem 0.8rem;">
                            <div style="font-weight:600;font-size:0.85rem;">{health['icon']} {cname[:25]}</div>
                            <div style="font-size:0.7rem;color:#64748b;margin-top:2px;">
                                {gd} | {html.escape(str(row.get('country','')))[:15]}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    next_stage = stages[i + 1]
                    for _, row in stage_df.iterrows():
                        health = _calc_health(row)
                        cname = html.escape(str(row['company_name']))
                        grade = str(row['customer_grade'])
                        gd = f"{grade}级" if grade in ('A', 'B', 'C') else grade
                        event_count = int(row.get('event_count', 0))
                        st.markdown(f"""
                        <div class="customer-card" style="padding:0.6rem 0.8rem;margin-bottom:0.4rem;">
                            <div style="font-weight:600;font-size:0.85rem;">{health['icon']} {cname[:25]}</div>
                            <div style="font-size:0.7rem;color:#64748b;margin-top:2px;">
                                {gd} | 跟进{event_count}次 | {health['label']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        rc1, rc2 = st.columns(2)
                        with rc1:
                            if st.button("查看", key=f"kv_{row['id']}", use_container_width=True):
                                st.session_state['selected_customer'] = row['id']
                                st.rerun()
                        with rc2:
                            if st.button(f"→ 推进", key=f"kp_{row['id']}", use_container_width=True):
                                db.update_customer(row['id'], {'development_status': next_stage})
                                db.add_timeline_event(row['id'], "更新信息",
                                    f"看板推进：{stage} → {next_stage}")
                                st.rerun()

def render_customer_detail():
    cid = st.session_state.get('selected_customer')
    if not cid:
        st.error("请先选择客户")
        return
    customer, err = db.get_customer(cid)
    if err or not customer:
        st.error("客户不存在或加载失败")
        return

    st.title(f"📋 {customer['company_name']}")
    if st.button("← 返回列表"):
        st.session_state['selected_customer'] = None
        st.rerun()
    st.markdown("---")

    # 基础信息
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("基础联系信息")
        st.write(f"**联系人：** {customer.get('contact_person', '未填写')}")
        st.write(f"**邮箱：** {customer.get('email', '未填写')}")
        st.write(f"**电话：** {customer.get('phone', '未填写')}")
        st.write(f"**WhatsApp：** {customer.get('whatsapp', '未填写')}")
        st.write(f"**国家：** {customer.get('country', '未填写')}")
        if customer.get('linkedin'):
            st.markdown(f"**LinkedIn：** <a href='{customer['linkedin']}' target='_blank'>🔗 打开主页</a>", unsafe_allow_html=True)
        st.write(f"**官网：** {customer.get('website', '未填写')}")
    with col2:
        st.subheader("客户评级与状态")
        grade = str(customer.get('customer_grade', 'C'))
        grade_display = f"{grade}级" if grade in ('A', 'B', 'C') else grade
        st.write(f"**客户等级：** {grade_display}")
        st.write(f"**跟进状态：** {customer['status']}")
        st.write(f"**行业：** {customer.get('industry', '未填写')}")
        st.write(f"**主营产品：** {customer.get('products', '未填写')}")
        st.write(f"**下次跟进：** {customer.get('follow_up_date', '未设置')}")

    st.markdown("---")
    st.subheader("📦 样品寄送管理")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**样品状态：** {customer.get('sample_status', '未寄出')}")
    with col2:
        st.write(f"**寄出日期：** {customer.get('sample_send_date', '未填写')}")
    with col3:
        st.write(f"**快递单号：** {customer.get('sample_tracking_number', '未填写')}")
    if customer.get('sample_feedback'):
        st.write(f"**客户反馈：** {customer['sample_feedback']}")

    st.markdown("---")
    st.subheader("📅 跟进时间轴")
    tl_df, _ = db.get_customer_timeline(cid)
    if tl_df.empty:
        st.info("暂无跟进记录")
    else:
        for _, e in tl_df.iterrows():
            st.markdown(f"""
            <div class="timeline-item">
                <div class="timeline-dot"></div>
                <div class="timeline-date">{e['created_at']}</div>
                <div class="timeline-content">
                    <strong>{e['event_type']}</strong><br/>{e['event_content']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📝 备注信息")
    st.write(customer.get('notes', '暂无备注'))

    st.markdown("---")
    st.subheader("📧 邮件发送历史")
    em_df, em_err = db.get_email_history(cid)
    if em_err:
        st.error(f"加载失败：{em_err}")
    elif em_df.empty:
        st.info("暂无邮件历史")
    else:
        for _, e in em_df.iterrows():
            with st.expander(f"版本{e['version']}｜{e['created_at']}"):
                st.write(f"**主题：** {e['email_subject']}")
                st.markdown("**内容：**")
                st.markdown(e['email_content'])

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✏️ 修改客户信息"):
            st.session_state['edit_customer'] = cid
            st.rerun()
    with col2:
        if st.button("🤖 AI生成开发信"):
            st.session_state['ai_email_customer'] = cid
            st.session_state['current_page'] = "跟进邮件工坊"
            st.rerun()
    with col3:
        if st.button("🔍 客户背景调研"):
            st.session_state['research_customer'] = cid
            st.session_state['current_page'] = "客户背景研究"
            st.rerun()

def render_customer_form(is_edit=False):
    if is_edit:
        cid = st.session_state.get('edit_customer')
        customer, err = db.get_customer(cid)
        if err or not customer:
            st.error("客户信息加载失败")
            return
        st.title("✏️ 编辑客户档案")
    else:
        customer = None
        st.title("➕ 新建客户档案")

    if st.button("← 返回上一页"):
        st.session_state.pop('show_add_form', None)
        st.session_state['edit_customer'] = None
        st.rerun()
    st.markdown("---")

    with st.form("customer_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("公司名称 *", value=customer['company_name'] if customer else "")
            contact_person = st.text_input("联系人", value=customer.get('contact_person', '') if customer else "")
            email = st.text_input("邮箱", value=customer.get('email', '') if customer else "")
            phone = st.text_input("电话", value=customer.get('phone', '') if customer else "")
            whatsapp = st.text_input("WhatsApp", value=customer.get('whatsapp', '') if customer else "")
            country = st.text_input("国家", value=customer.get('country', '') if customer else "")
            linkedin = st.text_input("LinkedIn链接", value=customer.get('linkedin', '') if customer else "")
            website = st.text_input("官网地址", value=customer.get('website', '') if customer else "")
        with col2:
            default_grades = ["A", "B", "C"]
            current_grade = customer.get('customer_grade', 'C') if customer else 'C'
            if current_grade not in default_grades:
                grade_options = default_grades + [current_grade]
            else:
                grade_options = default_grades
            customer_grade = st.selectbox("客户等级", grade_options,
                index=grade_options.index(current_grade) if current_grade in grade_options else 2)
            status = st.selectbox("跟进状态", ["正在跟进", "备选", "拒绝"], index=["正在跟进","备选","拒绝"].index(customer['status']) if customer else 1)
            industry = st.text_input("所属行业", value=customer.get('industry', '') if customer else "")
            products = st.text_input("主营产品", value=customer.get('products', '') if customer else "")
            follow_up_date = st.date_input("下次跟进日期", value=pd.to_datetime(customer['follow_up_date']).date() if (customer and customer.get('follow_up_date')) else datetime.now().date())

        st.markdown("---")
        st.subheader("📦 样品管理信息")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            sample_status = st.selectbox("样品状态", ["未寄出", "已寄出", "已收到", "已反馈"], index=["未寄出","已寄出","已收到","已反馈"].index(customer.get('sample_status','未寄出')) if customer else 0)
        with sc2:
            sample_send_date = st.date_input("寄出日期", value=pd.to_datetime(customer.get('sample_send_date')).date() if (customer and customer.get('sample_send_date')) else datetime.now().date())
        with sc3:
            sample_tracking_number = st.text_input("快递单号", value=customer.get('sample_tracking_number','') if customer else "")
        sample_feedback = st.text_area("样品反馈", value=customer.get('sample_feedback','') if customer else "")

        st.markdown("---")
        notes = st.text_area("备注信息", value=customer.get('notes','') if customer else "")
        submit = st.form_submit_button("💾 保存客户信息", type="primary")

        if submit:
            if not company_name.strip():
                st.error("公司名称为必填项")
                return
            data = {
                'company_name': company_name.strip(),
                'contact_person': contact_person,
                'email': email,
                'phone': phone,
                'whatsapp': whatsapp,
                'country': country,
                'linkedin': linkedin,
                'website': website,
                'customer_grade': customer_grade,
                'status': status,
                'industry': industry,
                'products': products,
                'follow_up_date': follow_up_date.strftime('%Y-%m-%d'),
                'sample_status': sample_status,
                'sample_send_date': sample_send_date.strftime('%Y-%m-%d'),
                'sample_tracking_number': sample_tracking_number,
                'sample_feedback': sample_feedback,
                'notes': notes
            }
            if is_edit:
                ok, err = db.update_customer(cid, data)
                if ok:
                    st.success("修改成功")
                else:
                    st.error(f"失败：{err}")
            else:
                cid_new, err = db.add_customer(data)
                if cid_new:
                    st.success("新建成功")
                else:
                    st.error(f"失败：{err}")
            st.session_state.pop('show_add_form', None)
            st.session_state['edit_customer'] = None
            st.rerun()
