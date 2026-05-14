import streamlit as st
from database.db import Database

db = Database()

def render_ai_email():
    cid = st.session_state.get('ai_email_customer')
    customer, err = db.get_customer(cid) if cid else (None, None)

    st.title("🤖 AI开发邮件生成")
    if st.button("← 返回客户详情"):
        st.session_state['current_page'] = "客户管理"
        st.rerun()
    st.markdown("---")

    # 修复空白问题：增加无客户提示
    if not customer:
        st.warning("⚠️ 请先从【客户详情】页面点击「AI生成开发信」按钮")
        st.info("操作步骤：客户管理 → 点击客户卡片的「查看详情」→ 点击「🤖 AI生成开发信」")
        return

    st.info(f"当前生成对象：**{customer['company_name']}**")
    st.markdown("---")

    # 加载系统配置（已植入你的SOP）
    company_intro = db.get_setting('company_intro')
    ai_prompt = db.get_setting('ai_email_prompt')

    with st.expander("📚 常州科旭SOP参考（自动加载）", expanded=False):
        st.text_area("公司英文定位", value=company_intro, height=120, disabled=True)
        st.text_area("开发信核心规则", value=ai_prompt, height=120, disabled=True)

    # 模板选择
    tpl_df, _ = db.get_all_templates()
    if not tpl_df.empty:
        st.subheader("📑 复用历史模板")
        tpl_opt = st.selectbox("选择模板", ["不使用模板"] + [f"{row['name']}(ID:{row['id']})" for _, row in tpl_df.iterrows()])
        if tpl_opt != "不使用模板":
            tid = int(tpl_opt.split("ID:")[1].replace(")", ""))
            tpl = tpl_df[tpl_df['id'] == tid].iloc[0]
            st.session_state['generated_email'] = {'subject': tpl['subject'], 'content': tpl['content']}

    # 邮件场景（完全按SOP分类）
    mail_type = st.selectbox("邮件场景", [
        "初次开发邮件（成本导向）",
        "初次开发邮件（技术导向）",
        "初次开发邮件（贸易商/分销商）",
        "跟进邮件（轻提醒+退路）",
        "跟进邮件（最后确认+留后路）",
        "拒绝回复（已有稳定供应商）",
        "拒绝回复（不采购原材料）",
        "季度轻触达（新产品/结构）",
    ])

    # 客户背调钩子（SOP要求：每封邮件必须有1个观察点）
    customer_hook = st.text_input("客户背调钩子（必填）", 
        placeholder="例如：看到你们的EN388 Cut D防割面料系列 / 你们专注于工业洗涤耐久的FR工装",
        help="从客户官网/LinkedIn提取1个具体观察点，这是高回复率的关键")

    # 产品切入点（SOP要求：每次只选1条）
    product_focus = st.selectbox("产品切入点（每次只选1个）", [
        "防切割纱线/面料（HPPE/芳纶）",
        "阻燃/耐高温纱线/面料（芳纶1313/1414）",
        "电弧防护面料（IEC 61482）",
        "焊接防护面料（EN ISO 11611）",
        "预氧化丝（PANOX）阻燃材料",
        "多功能复合防护材料"
    ])

    if st.button("✨ 一键生成符合SOP的开发信", type="primary"):
        if not customer_hook.strip():
            st.error("请填写客户背调钩子！这是SOP要求的必填项")
            return

        with st.spinner("正在生成符合常州科旭SOP的开发信..."):
            name = customer.get('contact_person') or "Sir/Madam"
            company = customer['company_name']

            # 完全按照你的SOP模板生成
            if mail_type == "初次开发邮件（成本导向）":
                subject = f"10-15% cost cut for your {product_focus.split('（')[0]}"
                content = f"""Hi {name},

{customer_hook}

We help factories reduce material cost without changing specs.

Would it make sense to compare one of your current items?

Best regards,
[Your Name]
KEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd.
WhatsApp: [你的号码]
Email: [你的邮箱]
"""

            elif mail_type == "初次开发邮件（技术导向）":
                subject = f"{product_focus.split('（')[0]} for your protective textiles"
                content = f"""Hi {name},

{customer_hook}

We focus on engineered protective yarns and fabrics for industrial PPE, with a focus on batch-to-batch consistency and industrial laundering durability.

Worth a short call if you're reviewing materials this quarter?

Best regards,
[Your Name]
KEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd.
WhatsApp: [你的号码]
Email: [你的邮箱]
"""

            elif mail_type == "初次开发邮件（贸易商/分销商）":
                subject = f"Improve margin on {product_focus.split('（')[0]}"
                content = f"""Hi {name},

We work with European distributors on aramid & HPPE yarn/fabric—often as margin improvement or stable backup supply.

Open to comparing one SKU when convenient?

Best regards,
[Your Name]
KEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd.
WhatsApp: [你的号码]
Email: [你的邮箱]
"""

            elif mail_type == "跟进邮件（轻提醒+退路）":
                subject = f"Re: {product_focus.split('（')[0]} for protective textiles"
                content = f"""Hi {name},

Just a quick note following up on my earlier message about aramid/HPPE materials for protective textiles.

No rush—may have missed in the inbox.

If it's not a priority now, totally fine.

Best regards,
[Your Name]
KEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd.
WhatsApp: [你的号码]
Email: [你的邮箱]
"""

            elif mail_type == "跟进邮件（最后确认+留后路）":
                subject = f"Re: {product_focus.split('（')[0]} materials"
                content = f"""Hi {name},

I'll keep this short—last check-in on aramid/HPPE materials for protective applications.

If this isn't relevant right now, no problem—I'll reconnect in a few months if anything changes.

Best regards,
[Your Name]
KEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd.
WhatsApp: [你的号码]
Email: [你的邮箱]
"""

            elif mail_type == "拒绝回复（已有稳定供应商）":
                subject = f"Re: {product_focus.split('（')[0]} | backup option"
                content = f"""Hi {name},

Totally understand—stability comes first.

We're happy to stay as a backup option if you ever need an alternative for aramid/HPPE.

I'll share occasional updates; feel free to reach out anytime.

Best regards,
[Your Name]
KEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd.
WhatsApp: [你的号码]
Email: [你的邮箱]
"""

            elif mail_type == "拒绝回复（不采购原材料）":
                subject = f"Re: {product_focus.split('（')[0]} | thanks"
                content = f"""Hi {name},

Thanks for clarifying.

If you ever meet fabric producers who need aramid/HPPE yarns, I'd appreciate an intro.

Best regards,
[Your Name]
KEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd.
WhatsApp: [你的号码]
Email: [你的邮箱]
"""

            elif mail_type == "季度轻触达（新产品/结构）":
                subject = f"New {product_focus.split('（')[0]} structure for protective textiles"
                content = f"""Hi {name},

Quick note—we've recently developed a lightweight {product_focus} structure for protective textiles.

If you're reviewing materials this quarter, happy to share details.

Best regards,
[Your Name]
KEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd.
WhatsApp: [你的号码]
Email: [你的邮箱]
"""

            else:
                subject = f"Re: {product_focus.split('（')[0]} | {company}"
                content = f"""Hi {name},

{customer_hook}

Quick question — are you currently reviewing your {product_focus} supply base?

No rush, just wanted to check if there's a fit.

Best regards,
[Your Name]
KEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd.
WhatsApp: [你的号码]
Email: [你的邮箱]
"""

            st.session_state['generated_email'] = {"subject": subject, "content": content}

    if 'generated_email' in st.session_state:
        st.markdown("---")
        st.subheader("📧 生成结果（完全符合SOP：≤5行、纯文本、低压力收尾）")
        mail = st.session_state['generated_email']
        subj = st.text_input("邮件主题", value=mail['subject'])
        cont = st.text_area("邮件内容", value=mail['content'], height=300)

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 保存到客户历史", type="primary"):
                v, err = db.add_email_history(cid, subj, cont)
                if v:
                    st.success(f"已保存为版本v{v}")
                else:
                    st.error(f"失败：{err}")
        with col2:
            if st.button("📋 复制全部内容"):
                st.markdown(f"""
<div style="background:#dcfce7; padding:8px 12px; border-radius:6px; text-align:center; margin-top:8px;">
✅ 已复制到剪贴板！
</div>
<script>
navigator.clipboard.writeText(`Subject: {subj}

{cont}`);
</script>
""", unsafe_allow_html=True)
        with col3:
            if st.button("💾 保存为模板"):
                st.session_state['show_save_template'] = True

        if st.session_state.get('show_save_template', False):
            with st.form("save_tpl"):
                tpl_name = st.text_input("模板名称")
                tpl_cat = st.selectbox("模板分类", ["开发邮件", "跟进邮件", "样品邮件", "其他"])
                if st.form_submit_button("确认保存"):
                    if not tpl_name:
                        st.warning("请填写模板名称")
                    else:
                        ok, err = db.add_email_template(tpl_name, tpl_cat, subj, cont)
                        if ok:
                            st.success("模板保存成功")
                            st.session_state['show_save_template'] = False
                            st.rerun()
                        else:
                            st.error(f"失败：{err}")
