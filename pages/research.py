import streamlit as st
from database.db import Database

db = Database()

def render_research():
    cid = st.session_state.get('research_customer')
    customer, err = db.get_customer(cid) if cid else (None, None)

    st.title("🔍 客户背景深度调研")
    if st.button("← 返回客户详情"):
        st.session_state['current_page'] = "客户详情"
        st.rerun()
    st.markdown("---")

    if not customer:
        st.error("请先选择客户")
        return
    st.subheader(f"调研对象：{customer['company_name']}")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 客户基础档案")
        st.write(f"**公司名称：** {customer['company_name']}")
        st.write(f"**国家：** {customer.get('country', '未填写')}")
        st.write(f"**行业：** {customer.get('industry', '未填写')}")
        st.write(f"**主营产品：** {customer.get('products', '未填写')}")
        st.write(f"**客户等级：** {customer['customer_grade']}级")
        st.write(f"**跟进状态：** {customer['status']}")

    with col2:
        st.subheader("🔗 快速访问链接")
        if customer.get('website') and customer['website'].strip():
            st.markdown(f"**官网：** <a href='{customer['website']}' target='_blank'>🔗 打开官网</a>", unsafe_allow_html=True)
        else:
            st.write("**官网：** 未填写")
            
        if customer.get('linkedin') and customer['linkedin'].strip():
            st.markdown(f"**LinkedIn：** <a href='{customer['linkedin']}' target='_blank'>🔗 打开LinkedIn</a>", unsafe_allow_html=True)
        else:
            st.write("**LinkedIn：** 未填写")

    st.markdown("---")
    st.subheader("📝 调研笔记")
    research_notes = st.text_area("在这里记录你的调研发现", height=200, 
        value=customer.get('notes', '') if customer else "")
    
    if st.button("💾 保存调研笔记", type="primary"):
        success, error = db.update_customer(cid, {'notes': research_notes})
        if success:
            st.success("调研笔记已保存")
        else:
            st.error(f"保存失败：{error}")

    st.markdown("---")
    st.subheader("📋 背调检查清单")
    st.checkbox("已查看公司官网，了解产品线")
    st.checkbox("已查看LinkedIn，找到关键联系人")
    st.checkbox("已确认客户有PPE/防护相关业务")
    st.checkbox("已确认客户有欧洲/北美市场")
    st.checkbox("已找到客户的认证信息")
    st.checkbox("已分析客户的竞争对手")