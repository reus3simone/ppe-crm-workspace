import streamlit as st
import html
from database.db import Database

db = Database()

# SOP 跟进模板库（从SOP文档提取）
FOLLOW_UP_TEMPLATES = {
    "首次跟进（第一封后7个工作日）": {
        "subject": "Quick follow-up on protective materials",
        "body": """Hi {name},

Just a quick note following up on my earlier message about aramid/HPPE materials for protective textiles.

No rush—may have missed in the inbox.
If it's not a priority now, totally fine.

Best regards,
{signature}"""
    },
    "二次跟进（10-14天后）": {
        "subject": "Re: protective materials | {company}",
        "body": """Hi {name},

I'll keep this short—last check-in on aramid/HPPE materials for protective applications.

If this isn't relevant right now, no problem—I'll reconnect in a few months if anything changes.

Best regards,
{signature}"""
    },
    "三次跟进（21天后，最后跟进）": {
        "subject": "Re: {company} | protective materials",
        "body": """Hi {name},

Quick note—we've recently developed a lightweight FR / softer cut-resistant yarn structure for protective textiles.

If you're reviewing materials this quarter, happy to share details.

Best regards,
{signature}"""
    },
    "季度轻触达（90天后）": {
        "subject": "Quick question about your protective textiles",
        "body": """Hi {name},

I saw more customers asking for industrial laundering durability / lightweight PPE lately.
Curious if you're seeing the same on your side.

Best regards,
{signature}"""
    },
    "拒绝回复（已有稳定供应商）": {
        "subject": "Re: {company}",
        "body": """Hi {name},

Totally understand—stability comes first.
We're happy to stay as a backup option if you ever need an alternative for aramid/HPPE.
I'll share occasional updates; feel free to reach out anytime.

Best regards,
{signature}"""
    },
    "拒绝回复（不采购原材料）": {
        "subject": "Re: {company}",
        "body": """Hi {name},

Thanks for clarifying.
If you ever meet fabric producers who need aramid/HPPE yarns, I'd appreciate an intro.

Best regards,
{signature}"""
    },
    "展会/领英跟进": {
        "subject": "Following up on your protective materials",
        "body": """Hi {name},

Nice connecting at {event}.

You mentioned exploring new aramid suppliers—are you running any material trials right now?

Best regards,
{signature}"""
    },
    "新产品/结构通知": {
        "subject": "New development in protective yarns",
        "body": """Hi {name},

Quick note—we've recently developed a new yarn structure for protective textiles that improves dexterity without dropping cut level.

If you're reviewing materials this quarter, happy to share details.

Best regards,
{signature}"""
    },
}


def render_ai_email():
    cid = st.session_state.get('ai_email_customer')
    customer, err = db.get_customer(cid) if cid else (None, None)

    st.title("📧 跟进邮件工坊")
    if st.button("← 返回客户详情"):
        st.session_state['current_page'] = "客户管理"
        st.rerun()
    st.markdown("---")

    if not customer:
        st.warning("⚠️ 请先从【客户详情】页面点击「AI生成开发信」按钮")
        st.info("操作步骤：客户管理 → 点击客户卡片的「查看详情」→ 点击「🤖 AI生成开发信」")
        return

    st.info(f"当前客户：**{customer['company_name']}** （{customer.get('country', '未知国家')}）")

    # 跟进轮次显示
    stats, _ = db.get_customer_follow_up_stats(cid)
    if stats:
        st.caption(f"已发送邮件：{stats['email_count']}封 | 跟进记录：{stats['follow_up_count']}次")
    next_date, next_msg = db.calculate_next_follow_up(cid)
    if next_date:
        st.caption(f"📅 {next_msg}（{next_date}）")

    st.markdown("---")

    # ===== 主操作区：模板选择 =====
    col1, col2 = st.columns([3, 2])

    with col1:
        scenario = st.selectbox("选择跟进场景",
            list(FOLLOW_UP_TEMPLATES.keys()),
            index=0)

        template = FOLLOW_UP_TEMPLATES[scenario]
        name = customer.get('contact_person') or 'Sir/Madam'
        company = customer['company_name']
        signature = "Elsa\nKEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd."

        # 需要额外字段的场景
        event_name = ""
        if scenario == "展会/领英跟进":
            event_name = st.text_input("展会/活动名称", placeholder="例如：A+A 2026")
            template_body = template['body'].format(name=name, company=company, signature=signature, event=event_name or "[展会名]")
        else:
            template_body = template['body'].format(name=name, company=company, signature=signature)

        subject = st.text_input("邮件主题", value=template['subject'].replace('{company}', company))
        content = st.text_area("邮件内容", value=template_body, height=280)

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("💾 保存到跟进历史", type="primary"):
                if not customer.get('contact_person'):
                    # If no contact person, still allow saving
                    pass
                v, err = db.record_follow_up(cid, subject, content)
                if v:
                    st.success(f"✅ 跟进邮件 v{v} 已保存")
                else:
                    st.error(f"保存失败：{err}")
        with c2:
            if st.button("📋 复制全部内容"):
                st.code(f"Subject: {subject}\n\n{content}", language=None)
                st.success("⬆ 点击上方代码块即可全选复制")
        with c3:
            if st.button("💾 保存为模板"):
                st.session_state['show_save_template'] = True

        if st.session_state.get('show_save_template', False):
            with st.form("save_tpl"):
                tpl_name = st.text_input("模板名称")
                tpl_cat = st.selectbox("模板分类", ["跟进邮件", "开发邮件", "样品邮件", "其他"])
                if st.form_submit_button("确认保存"):
                    if not tpl_name:
                        st.warning("请填写模板名称")
                    else:
                        ok, err = db.add_email_template(tpl_name, tpl_cat, subject, content)
                        if ok:
                            st.success("模板保存成功")
                            st.session_state['show_save_template'] = False
                            st.rerun()
                        else:
                            st.error(f"失败：{err}")

    # ===== 右侧：SOP参考面板 =====
    with col2:
        st.subheader("📚 SOP参考")
        with st.expander("🎯 开场句库（背调钩子）"):
            st.markdown("""
**官网产品线钩子：**
- I came across your [FR workwear/arc-rated/cut-resistant] range on your website.
- Noticed your focus on [industrial laundering/lightweight FR/high-dexterity cut protection].

**新闻/展会/认证钩子：**
- Saw your update about [new product/certification/exhibition] recently.
- Noticed your team has been active around [A+A/Intersec] this year.

**职位与语境钩子（技术岗）：**
- I'm reaching out as we work on similar protective textile material systems.
- Quick question from a materials side: how do you usually balance [cut level vs dexterity]?
            """)

        with st.expander("📝 主题行库（分场景）"):
            st.markdown("""
**成本导向（工厂/老板）：**
- 10-15% cost cut for your cut-resistant materials
- Stable backup supply for aramid materials

**技术方向：**
- Cut-resistant materials for your protective knits
- Aramid yarn systems for FR applications

**通用安全款：**
- Quick question about your protective fabrics
- Regarding your PPE material supply

**跟进用：**
- Quick follow-up on protective materials
- Re: [company] | protective textiles
            """)

        with st.expander("💬 低压力收尾库"):
            st.markdown("""
**Yes/No（最省回复成本）：**
- Would it be relevant to compare one item you're currently using?
- Are you reviewing any [FR/arc/cut] materials this quarter?

**给退路：**
- If this isn't on your roadmap now, totally fine—I can check back later.
- If someone else owns materials evaluation on your side, happy to reach out to the right person.
            """)

        with st.expander("⛔ 禁用词提醒"):
            st.markdown("""
**开发信禁用：**
- ❌ We are a professional manufacturer…
- ❌ Good quality & best price
- ❌ Leading supplier
- ❌ Please find our catalog attached

**跟进禁用：**
- ❌ Did you see my email?
- ❌ Please let me know if you are interested
            """)

        with st.expander("📐 跟进节奏"):
            st.markdown("""
| 轮次 | 间隔 | 动作 |
|---|---|---|
| 第1封 | - | 开发信 |
| 跟进1 | ≥7个工作日 | 轻提醒+退路 |
| 跟进2 | 10-14天 | 最后确认 |
| 跟进3 | 21天 | 留后路 |
| 后续 | 90天 | 季度轻触达 |
            """)

    # ===== 历史邮件查看 =====
    st.markdown("---")
    st.subheader("📜 该客户邮件历史")
    em_df, em_err = db.get_email_history(cid)
    if em_err:
        st.error(f"加载失败：{em_err}")
    elif em_df.empty:
        st.info("暂无邮件历史")
    else:
        for _, e in em_df.iterrows():
            with st.expander(f"版本v{e['version']}｜{e['created_at']}"):
                st.write(f"**主题：** {e['email_subject']}")
                st.markdown("**内容：**")
                st.markdown(e['email_content'])
