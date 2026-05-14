import streamlit as st
import pandas as pd
from datetime import datetime
from database.db import Database

db = Database()

def get_follow_up_reminders():
    """修复：日期比较报错问题"""
    df, err = db.get_all_customers()
    if err or df.empty:
        return []
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        # 修复：统一转日期格式，过滤空值，避免类型报错
        df['follow_up_date'] = pd.to_datetime(df['follow_up_date'], errors='coerce').dt.strftime('%Y-%m-%d')
        df_clean = df[df['follow_up_date'].notna()]
        reminders = df_clean[df_clean['follow_up_date'] <= today].to_dict('records')
        return reminders
    except Exception:
        return []

def import_customers_from_excel(uploaded_file):
    """修复：Excel表格导入功能"""
    try:
        df = pd.read_excel(uploaded_file)
        # 自动匹配字段名，兼容各种表头
        column_map = {
            '公司名': 'company_name', '公司名称': 'company_name', 'company': 'company_name',
            '联系人': 'contact_person', '姓名': 'contact_person', 'name': 'contact_person',
            '邮箱': 'email', 'email': 'email', '邮件': 'email',
            '电话': 'phone', 'phone': 'phone', '手机号': 'phone',
            '国家': 'country', 'country': 'country',
            '官网': 'website', 'website': 'website',
            'LinkedIn': 'linkedin', '领英': 'linkedin',
            '行业': 'industry', 'products': 'products', '产品': 'products'
        }
        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
        
        success_count = 0
        fail_count = 0
        for _, row in df.iterrows():
            row_dict = dict(row)
            if 'company_name' not in row_dict or not str(row_dict['company_name']).strip():
                fail_count += 1
                continue
            # 自动去重
            conflict_level, _ = db.check_customer_conflict(row_dict)
            if conflict_level == 3:
                fail_count += 1
                continue
            cid, _ = db.add_customer(row_dict)
            if cid:
                success_count += 1
            else:
                fail_count += 1
        return success_count, fail_count
    except Exception as e:
        return 0, 0

def render_home_page():
    st.title("📊 PPE客户开发工作区")
    st.markdown("---")

    # 表格导入功能
    with st.expander("📥 批量导入客户Excel", expanded=False):
        uploaded_file = st.file_uploader("上传Excel表格", type=["xlsx", "xls"])
        if uploaded_file:
            if st.button("开始导入", type="primary"):
                success, fail = import_customers_from_excel(uploaded_file)
                st.success(f"导入完成！成功：{success}条，重复/失败：{fail}条")
                st.rerun()

    df, err = db.get_all_customers()
    if err:
        st.error("数据加载失败")
        return

    total = len(df)
    a_grade = len(df[df['customer_grade'] == 'A'])
    b_grade = len(df[df['customer_grade'] == 'B'])
    pending = len(df[df['development_status'] == '初次开发'])
    quoted = len(df[df['development_status'] == '已报价'])
    sample = len(df[df['development_status'] == '样品阶段'])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总客户数", total)
    col2.metric("A级客户", a_grade)
    col3.metric("B级客户", b_grade)
    col4.metric("待开发", pending)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("已报价", quoted)
    col2.metric("样品阶段", sample)
    reminders = get_follow_up_reminders()
    col3.metric("今日待跟进", len(reminders))

    # 待跟进提醒
    if reminders:
        st.markdown("---")
        st.warning("⚠️ 今日待跟进客户")
        for c in reminders:
            st.write(f"• {c['company_name']} | 上次跟进：{c.get('follow_up_date', '')}")

    st.markdown("---")
    st.subheader("📈 最近新增客户")
    if not df.empty:
        st.dataframe(
            df[['company_name', 'country', 'customer_grade', 'development_status', 'assigned_to', 'created_at']].head(10),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("暂无客户数据，快去添加第一个客户吧！")

    st.markdown("---")
    st.subheader("📌 快速操作")
    col1, col2, col3 = st.columns(3)
    if col1.button("➕ 新增客户", use_container_width=True):
        st.session_state['show_add_form'] = True
        st.session_state['current_page'] = "客户管理"
        st.rerun()
    if col2.button("🤖 生成开发邮件", use_container_width=True):
        st.session_state['current_page'] = "AI邮件生成"
        st.rerun()
    if col3.button("🔍 客户背景研究", use_container_width=True):
        st.session_state['current_page'] = "客户背景研究"
        st.rerun()
