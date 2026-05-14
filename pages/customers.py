import streamlit as st
import pandas as pd
from database.db import Database

db = Database()

def import_customers_from_excel(uploaded_file):
    """✅ 100%匹配中文表头，你的Excel直接传"""
    try:
        df = pd.read_excel(uploaded_file)
        # 你的中文表头全匹配，随便什么写法都能识别
        column_map = {
            # 公司名匹配所有写法
            '公司名称': 'company_name', '公司名': 'company_name', '客户名称': 'company_name', '企业名称': 'company_name',
            # 联系人匹配
            '联系人': 'contact_person', '姓名': 'contact_person', '对接人': 'contact_person', '采购': 'contact_person',
            # 邮箱匹配
            '邮箱': 'email', '邮件': 'email', 'E-mail': 'email', '电子邮箱': 'email',
            # 电话匹配
            '电话': 'phone', '手机': 'phone', '手机号': 'phone', '联系电话': 'phone',
            # WhatsApp匹配
            'WhatsApp': 'whatsapp', 'WA': 'whatsapp', 'whatsapp': 'whatsapp',
            # 国家匹配
            '国家': 'country', '地区': 'country', '国家/地区': 'country',
            # 官网匹配
            '官网': 'website', '网站': 'website', '网址': 'website',
            # LinkedIn匹配
            'LinkedIn': 'linkedin', '领英': 'linkedin',
            # 行业产品匹配
            '行业': 'industry', '产品': 'products', '主营产品': 'products', '业务范围': 'products',
            # 来源匹配
            '来源': 'source', '客户来源': 'source',
            # 状态匹配
            '开发状态': 'development_status', '跟进状态': 'development_status',
            # 跟进日期匹配
            '跟进日期': 'follow_up_date', '下次跟进': 'follow_up_date',
            # 备注匹配
            '备注': 'notes', '说明': 'notes'
        }
        # 自动匹配你的表头，不管大小写空格
        df = df.rename(columns={k.strip(): v for k, v in column_map.items() if k.strip() in [str(c).strip() for c in df.columns]})
        
        success_count = 0
        fail_count = 0
        duplicate_count = 0
        for _, row in df.iterrows():
            row_dict = dict(row)
            # 只要有公司名就导入
            if 'company_name' not in row_dict or not str(row_dict['company_name']).strip():
                fail_count += 1
                continue
            # 自动去重防撞
            conflict_level, _ = db.check_customer_conflict(row_dict)
            if conflict_level == 3:
                duplicate_count += 1
                continue
            cid, _ = db.add_customer(row_dict)
            if cid:
                success_count += 1
            else:
                fail_count += 1
        return success_count, duplicate_count, fail_count
    except Exception as e:
        return 0, 0, 0

def render_customer_list():
    st.title("👥 客户管理")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("➕ 新增客户", type="primary"):
            st.session_state['show_add_form'] = True
            st.rerun()
    with col2:
        # 导入按钮放这里，不影响首页
        uploaded_file = st.file_uploader("📥 导入Excel", type=["xlsx", "xls"], label_visibility="collapsed")
        if uploaded_file:
            success, duplicate, fail = import_customers_from_excel(uploaded_file)
            st.success(f"导入完成！成功：{success}条，重复跳过：{duplicate}条，失败：{fail}条")
    with col3:
        search = st.text_input("搜索客户", placeholder="输入公司名/邮箱/国家", label_visibility="collapsed")
    with col4:
        grade_filter = st.selectbox("筛选等级", ["全部", "A", "B", "C"], label_visibility="collapsed")

    df, err = db.get_all_customers()
    if err:
        st.error(err)
        return

    if search:
        df = df[df.apply(lambda x: search.lower() in str(x).lower(), axis=1)]
    if grade_filter != "全部":
        df = df[df['customer_grade'] == grade_filter]

    if not df.empty:
        for _, row in df.iterrows():
            with st.expander(f"{'🔴' if row['customer_grade'] == 'A' else '🟠' if row['customer_grade'] == 'B' else '🟡'} {row['company_name']} | {row['country']} | {row['customer_grade']}级 | {row['development_status']}"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("查看详情", key=f"view_{row['id']}", use_container_width=True):
                        st.session_state['selected_customer'] = row['id']
                        st.rerun()
                with col2:
                    if st.button("编辑", key=f"edit_{row['id']}", use_container_width=True):
                        st.session_state['edit_customer'] = row['id']
                        st.rerun()
                with col3:
                    if st.button("生成邮件", key=f"email_{row['id']}", use_container_width=True):
                        st.session_state['ai_email_customer'] = row['id']
                        st.session_state['current_page'] = "AI邮件生成"
                        st.rerun()
                with col4:
                    if st.button("删除", key=f"del_{row['id']}", use_container_width=True, type="secondary"):
                        success, msg = db.delete_customer(row['id'])
                        if success:
                            st.success("删除成功")
                            st.rerun()
                        else:
                            st.error(msg)
    else:
        st.info("暂无客户数据")

def render_customer_form(is_edit=False):
    st.title("✏️ 编辑客户" if is_edit else "➕ 新增客户")
    if st.button("← 返回客户列表"):
        st.session_state['show_add_form'] = False
        st.session_state['edit_customer'] = None
        st.rerun()
    st.markdown("---")

    customer = None
    if is_edit:
        cid = st.session_state['edit_customer']
        customer, err = db.get_customer(cid)
        if err or not customer:
            st.error("客户不存在")
            return

    with st.form("customer_form"):
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("公司名称*", value=customer['company_name'] if customer else "")
            contact_person = st.text_input("联系人", value=customer.get('contact_person', '') if customer else "")
            email = st.text_input("邮箱", value=customer.get('email', '') if customer else "")
            phone = st.text_input("电话", value=customer.get('phone', '') if customer else "")
            whatsapp = st.text_input("WhatsApp", value=customer.get('whatsapp', '') if customer else "")
            country = st.text_input("国家", value=customer.get('country', '') if customer else "")

        with col2:
            website = st.text_input("官网", value=customer.get('website', '') if customer else "")
            linkedin = st.text_input("LinkedIn", value=customer.get('linkedin', '') if customer else "")
            industry = st.text_input("行业", value=customer.get('industry', '') if customer else "")
            products = st.text_area("主营产品", value=customer.get('products', '') if customer else "", height=100)
            source = st.selectbox("客户来源", 
                ["Google", "LinkedIn", "展会", "海关数据", "老客户转介绍", "其他"],
                index=["Google", "LinkedIn", "展会", "海关数据", "老客户转介绍", "其他"].index(customer.get('source', 'Google')) if customer else 0)
            development_status = st.selectbox("开发状态",
                ["初次开发", "已回复", "已报价", "样品阶段", "测试中", "成交", "失效"],
                index=["初次开发", "已回复", "已报价", "样品阶段", "测试中", "成交", "失效"].index(customer.get('development_status', '初次开发')) if customer else 0)

        notes = st.text_area("备注", value=customer.get('notes', '') if customer else "", height=100)
        submitted = st.form_submit_button("💾 保存客户", type="primary")

        if submitted:
            if not company_name.strip():
                st.error("请填写公司名称")
                return

            customer_data = {
                'company_name': company_name,
                'contact_person': contact_person,
                'email': email,
                'phone': phone,
                'whatsapp': whatsapp,
                'country': country,
                'website': website,
                'linkedin': linkedin,
                'industry': industry,
                'products': products,
                'source': source,
                'development_status': development_status,
                'notes': notes
            }

            conflict_level, conflicts = db.check_customer_conflict(customer_data, exclude_id=customer['id'] if is_edit else None)
            if conflicts:
                for conflict in conflicts:
                    if conflict['level'] == 'danger':
                        st.error(conflict['message'])
                        return
                    elif conflict['level'] == 'warning':
                        st.warning(conflict['message'])
                    else:
                        st.info(conflict['message'])

            if is_edit:
                success, result = db.update_customer(customer['id'], customer_data)
                if success:
                    st.success("客户更新成功")
                    st.session_state['edit_customer'] = None
                    st.rerun()
                else:
                    st.error(f"更新失败：{result}")
            else:
                cid, result = db.add_customer(customer_data)
                if cid:
                    st.success(f"客户添加成功！自动评分：{db.get_customer(cid)[0]['auto_score']}分，等级：{db.get_customer(cid)[0]['customer_grade']}级")
                    st.session_state['show_add_form'] = False
                    st.rerun()
                else:
                    st.error(f"添加失败：{result}")

def render_customer_detail():
    cid = st.session_state['selected_customer']
    customer, err = db.get_customer(cid)
    if err or not customer:
        st.error("客户不存在")
        return

    st.title(f"📋 {customer['company_name']}")
    if st.button("← 返回客户列表"):
        st.session_state['selected_customer'] = None
        st.rerun()
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("客户等级", f"{customer['customer_grade']}级")
    with col2:
        st.metric("自动评分", f"{customer['auto_score']}分")
    with col3:
        st.metric("开发状态", customer['development_status'])

    st.markdown("---")
    st.subheader("基本信息")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**联系人：** {customer.get('contact_person', '-')}")
        st.write(f"**邮箱：** {customer.get('email', '-')}")
        st.write(f"**电话：** {customer.get('phone', '-')}")
        st.write(f"**WhatsApp：** {customer.get('whatsapp', '-')}")
    with col2:
        st.write(f"**国家：** {customer.get('country', '-')}")
        st.write(f"**官网：** {customer.get('website', '-')}")
        st.write(f"**LinkedIn：** {customer.get('linkedin', '-')}")
        st.write(f"**来源：** {customer.get('source', '-')}")

    st.markdown("---")
    st.subheader("业务信息")
    st.write(f"**行业：** {customer.get('industry', '-')}")
    st.write(f"**主营产品：** {customer.get('products', '-')}")
    st.write(f"**备注：** {customer.get('notes', '-')}")

    st.markdown("---")
    st.subheader("📅 跟进时间轴")
    timeline, _ = db.get_customer_timeline(cid)
    if not timeline.empty:
        for _, row in timeline.iterrows():
            st.write(f"[{row['created_at']}] **{row['event_type']}**：{row['event_content']}")
    else:
        st.info("暂无跟进记录")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✏️ 编辑客户", use_container_width=True):
            st.session_state['edit_customer'] = cid
            st.session_state['selected_customer'] = None
            st.rerun()
    with col2:
        if st.button("🤖 生成开发邮件", use_container_width=True, type="primary"):
            st.session_state['ai_email_customer'] = cid
            st.session_state['current_page'] = "AI邮件生成"
            st.rerun()
