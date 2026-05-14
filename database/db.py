# 在render_customer_form函数开头添加冲突检测逻辑
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
            
            # 新增字段下拉
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
                st.error("公司名称不能为空")
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

            # 冲突检测
            conflict_level, conflicts = db.check_customer_conflict(customer_data, exclude_id=customer['id'] if is_edit else None)
            
            # 显示冲突提醒
            if conflicts:
                for conflict in conflicts:
                    if conflict['level'] == 'danger':
                        st.error(conflict['message'])
                        st.caption(conflict['details'])
                        return
                    elif conflict['level'] == 'warning':
                        st.warning(conflict['message'])
                        st.caption(conflict['details'])
                    else:
                        st.info(conflict['message'])
                        st.caption(conflict['details'])

            if is_edit:
                success, result = db.update_customer(customer['id'], customer_data)
                if success:
                    st.success("客户更新成功")
                    if isinstance(result, list) and result:
                        st.info("注意：存在潜在冲突，已记录到跟进时间轴")
                    st.session_state['edit_customer'] = None
                    st.rerun()
                else:
                    st.error(f"更新失败：{result}")
            else:
                cid, result = db.add_customer(customer_data)
                if cid:
                    st.success(f"客户新增成功 | 自动评分：{db.get_customer(cid)[0]['auto_score']}分 | 等级：{db.get_customer(cid)[0]['customer_grade']}级")
                    if isinstance(result, list) and result:
                        st.info("注意：存在潜在冲突，已记录到跟进时间轴")
                    st.session_state['show_add_form'] = False
                    st.rerun()
                else:
                    st.error(f"新增失败：{result}")
