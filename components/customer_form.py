import streamlit as st
import pandas as pd
from datetime import datetime
from database.db import Database

db = Database()


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
