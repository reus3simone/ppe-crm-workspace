import streamlit as st
import pandas as pd
from datetime import date
from database.db import Database

from components.import_dialog import render_import_dialog
from components.customer_form import render_new_customer_form, render_edit_form
from components.customer_detail import render_customer_detail
from components.customer_list import render_customer_list

db = Database()


def render_workspace():
    st.title("👥 客户工作台")
    st.markdown("---")

    # ── 加载数据 ──
    df, err = db.get_all_customers_with_stats()
    if err:
        st.error(f"数据加载失败：{err}")
        return

    # ── 顶部操作栏 ──
    c1, c2, c3, c4 = st.columns([2, 1.2, 1, 1.2])
    with c1:
        search_key = st.text_input("🔍 搜索", placeholder="公司 / 联系人 / 邮箱 / 电话 / 国家 / 产品",
                                   label_visibility="collapsed")
    with c2:
        all_countries = sorted(df['country'].dropna().unique()) if not df.empty else []
        country_filter = st.selectbox("国家", ["全部"] + [c for c in all_countries if c.strip()],
                                      label_visibility="collapsed")
    with c3:
        if st.button("➕ 新建", type="secondary", use_container_width=True):
            st.session_state['ws_new_customer'] = True
            st.rerun()
    with c4:
        if st.button("📥 批量导入", type="primary", use_container_width=True):
            st.session_state['ws_show_import'] = True
            st.rerun()

    # ── 快捷筛选标签 ──
    tag_options = ["全部", "A级", "B级", "C级", "初次开发", "已发开发信", "已报价", "样品阶段", "已成交", "逾期"]
    active_tag = st.session_state.get('ws_filter_tag', '全部')
    selected = st.pills("筛选", tag_options, selection_mode="single",
                        default=active_tag, key="filter_pills",
                        label_visibility="collapsed")
    if selected and selected != active_tag:
        st.session_state['ws_filter_tag'] = selected
        st.session_state['ws_page'] = 0
        st.rerun()

    # ── 弹窗 / 表单 ──
    if st.session_state.get('ws_show_import', False):
        render_import_dialog()
        return
    if st.session_state.get('ws_new_customer', False):
        render_new_customer_form()
        return
    edit_id = st.session_state.get('ws_edit_id')
    if edit_id:
        edit_customer, err = db.get_customer(edit_id)
        if edit_customer:
            render_edit_form(edit_customer)
            return

    # ── 过滤 ──
    if search_key:
        sk = search_key.lower()
        df = df[
            df['company_name'].str.contains(sk, case=False, na=False) |
            df['contact_person'].str.contains(sk, case=False, na=False) |
            df['email'].str.contains(sk, case=False, na=False) |
            df['phone'].str.contains(sk, case=False, na=False) |
            df['whatsapp'].str.contains(sk, case=False, na=False) |
            df['country'].str.contains(sk, case=False, na=False) |
            df['products'].str.contains(sk, case=False, na=False)
        ]
    if country_filter != "全部":
        df = df[df['country'] == country_filter]
    if active_tag != "全部":
        if active_tag in ("A级", "B级", "C级"):
            df = df[df['customer_grade'] == active_tag[0]]
        elif active_tag == "初次开发":
            df = df[df['development_status'] == active_tag]
        elif active_tag == "已发开发信":
            df = df[df['development_status'].str.contains('已发', na=False) &
                     df['development_status'].str.contains('开发信', na=False)]
        elif active_tag == "逾期":
            today = date.today()
            mask = df['follow_up_date'].notna() & (pd.to_datetime(df['follow_up_date']).dt.date < today)
            df = df[mask]
        else:
            df = df[df['development_status'] == active_tag]

    # ── 分栏布局 ──
    left_col, right_col = st.columns([0.38, 0.62])
    selected_id = st.session_state.get('ws_selected_id')
    page = st.session_state.get('ws_page', 0)

    with left_col:
        render_customer_list(df, selected_id, page)

    with right_col:
        if not selected_id:
            st.info("👈 请从左侧选择一个客户")
            st.stop()

        customer, err = db.get_customer(selected_id)
        if err or not customer:
            st.error("客户不存在")
            st.stop()

        render_customer_detail(customer)
