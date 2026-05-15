import streamlit as st
from database.db import Database

db = Database()

def render_research():
    cid = st.session_state.get('research_customer')
    customer, err = db.get_customer(cid) if cid else (None, None)

    st.title("🔍 客户背景深度调研")
    if st.button("← 返回客户详情"):
        st.session_state['current_page'] = "客户管理"
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
        grade = str(customer.get('customer_grade', 'C'))
        grade_display = f"{grade}级" if grade in ('A', 'B', 'C') else grade
        st.write(f"**客户等级：** {grade_display}")
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

    # ===== 产品匹配建议 =====
    st.subheader("🔗 产品匹配建议")
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
        st.info("暂未匹配到产品线，请填写更多客户信息")
    # 手动补充匹配
    manual_product = st.text_input("手动指定匹配产品（选填）",
        placeholder="例如：阻燃面料、防切割纱线等",
        key="research_manual_product")

    # ===== 建议发送时间 =====
    st.subheader("🕐 建议发送时间")
    tz_info = db.get_timezone_advice(customer.get('country', ''))
    if tz_info:
        st.markdown(f"""
        - **客户时区：** {tz_info['tz']}
        - **最佳发送：** 客户当地 09:30 = 北京时间 **{tz_info['cst_send']}**
        - **推荐日期：** 周二至周四
        """)
    else:
        st.info("未识别客户时区，请填写国家信息")

    st.markdown("---")
    st.subheader("📝 调研笔记")
    research_notes = st.text_area("在这里记录你的调研发现", height=200, 
        value=customer.get('notes', '') if customer else "")
    
    if st.button("💾 保存调研笔记", type="primary"):
        success, error = db.update_customer(cid, {'notes': research_notes})
        if success:
            # 自动记录到跟进时间轴
            match_text = ""
            if matches:
                match_text = "匹配产品：" + "、".join([m['product'] for m in matches])
            if manual_product:
                match_text += f"（手动补充：{manual_product}）"
            time_text = ""
            if tz_info:
                time_text = f"建议发送时段：北京{tz_info['cst_send']}"
            timeline_parts = [p for p in ["背调完成", match_text, time_text] if p]
            db.add_timeline_event(cid, "背调完成", " | ".join(timeline_parts))
            st.success("调研笔记已保存")
        else:
            st.error(f"保存失败：{error}")

    st.markdown("---")
    st.subheader("📋 背调检查清单（SOP十四·官网快筛）")
    st.checkbox("已查看公司官网，了解产品线")
    st.checkbox("已查看LinkedIn，找到关键联系人")
    st.checkbox("命中PPE/防护技术语言（EN388/EN11612/IEC61482/NFPA2112等）")
    st.checkbox("有真实应用场景，非纯素材站")
    st.checkbox("有开发能力（R&D/textile engineering/fabric development）")
    st.checkbox("公司活跃（LinkedIn/新闻/展会/新品动态）")
    st.checkbox("已确认客户有欧洲/北美市场")
    st.checkbox("已提取1个钩子（产品线/新闻/认证/展会/材料词）")