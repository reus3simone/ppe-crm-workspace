import streamlit as st
from database.db import Database

db = Database()

SYSTEM_PROMPT = """你是常州科旭纺织（KEYSTONE / Jiangsu Kexu Textile Technology Co., Ltd.）的外贸开发邮件撰写助手。
公司定位：短纤体系高性能防护纺织品供应商，核心方向为芳纶/阻燃/防切割/电弧/高温防护材料，面向工业PPE和特种工装客户。

你必须严格遵守以下SOP铁律写开发邮件：
1. 正文≤5行，短、克制、纯文本格式
2. 每封只讲1个客户观察点或1个痛点
3. 低压力收尾，给客户保留不回复的空间
4. 禁用以下套话：We are a professional manufacturer / Best price / Leading supplier / high quality
5. 第一封邮件：无附件、无链接、无PDF、无目录
6. 标题像同事日常往来，含客户业务关键词；禁用 offer/discount/supplier/best price 在标题中
7. 语气：专业同行感，不推销、不卑微
8. 签名固定：KEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd.
9. 用英文撰写全部邮件内容

公司英文定位（可适度融入，勿堆砌）：
We engineer staple-fiber protective yarns and fabrics for industrial PPE—cut resistance, FR / heat protection, and arc-related protective textiles—with in-house yarn spinning and fabric engineering capabilities.

输出格式（严格遵守，只输出以下内容）：
主题：[邮件标题]
正文：
[邮件正文，纯文本，≤5行]
"""


def build_user_prompt(customer, mail_type, customer_hook, product_focus):
    """根据客户数据和用户选择构建 prompt"""
    ctx_parts = []
    ctx_parts.append(f"客户公司：{customer['company_name']}")
    if customer.get('country'):
        ctx_parts.append(f"国家：{customer['country']}")
    if customer.get('industry'):
        ctx_parts.append(f"公司定位/行业：{customer['industry']}")
    if customer.get('products'):
        ctx_parts.append(f"业务对接/产品：{customer['products']}")
    if customer.get('development_status'):
        ctx_parts.append(f"开发进度：{customer['development_status']}")
    if customer.get('notes'):
        ctx_parts.append(f"备注/调研笔记：{customer['notes']}")

    ctx_parts.append(f"\n邮件场景：{mail_type}")
    ctx_parts.append(f"客户背调钩子（必须融入正文第一句）：{customer_hook}")
    ctx_parts.append(f"产品切入点：{product_focus}")
    ctx_parts.append(f"收件人称呼：{customer.get('contact_person') or 'Sir/Madam'}")

    return "\n".join(ctx_parts)


def call_claude_api(system_prompt, user_prompt, api_key):
    """调用 Anthropic Claude API 生成邮件"""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


def parse_email_response(text):
    """解析 AI 返回的邮件内容，提取主题和正文"""
    subject = ""
    body = text
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('主题：') or stripped.startswith('Subject:'):
            subject = stripped.split('：', 1)[-1].split(':', 1)[-1].strip()
        elif stripped.startswith('正文：') or stripped.startswith('正文:'):
            body = stripped.split('：', 1)[-1].split(':', 1)[-1].strip()
    if not subject:
        # 尝试取第一行非空内容作为主题
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            first = lines[0]
            if len(first) < 120 and 'KEYSTONE' not in first:
                subject = first
                body = '\n'.join(lines[1:]) if len(lines) > 1 else text
    return subject, body


def render_ai_email():
    cid = st.session_state.get('ai_email_customer')
    customer, err = db.get_customer(cid) if cid else (None, None)

    st.title("🤖 AI开发邮件生成")
    if st.button("← 返回客户详情"):
        st.session_state['current_page'] = "客户管理"
        st.rerun()
    st.markdown("---")

    if not customer:
        st.warning("⚠️ 请先从【客户详情】页面点击「AI生成开发信」按钮")
        st.info("操作步骤：客户管理 → 点击客户卡片的「查看详情」→ 点击「🤖 AI生成开发信」")
        return

    st.info(f"当前生成对象：**{customer['company_name']}**")

    # API Key 设置
    with st.expander("⚙️ AI设置", expanded=False):
        api_key = st.text_input("Anthropic API Key",
            value=st.session_state.get('ai_api_key', ''),
            type="password",
            placeholder="sk-ant-...",
            help="在 console.anthropic.com 获取。留空则使用本地模板模式。")
        if api_key:
            st.session_state['ai_api_key'] = api_key
        st.caption("Key 仅存于当前会话，不会写入数据库。")
    st.markdown("---")

    # 加载 SOP 参考
    company_intro = db.get_setting('company_intro')
    ai_prompt = db.get_setting('ai_email_prompt')
    with st.expander("📚 SOP规则参考", expanded=False):
        st.text_area("公司英文定位", value=company_intro, height=100, disabled=True)
        st.text_area("开发信核心规则", value=ai_prompt, height=100, disabled=True)

    # 历史模板
    tpl_df, _ = db.get_all_templates()
    if not tpl_df.empty:
        st.subheader("📑 复用历史模板")
        tpl_opt = st.selectbox("选择模板", ["不使用模板"] + [f"{row['name']}(ID:{row['id']})" for _, row in tpl_df.iterrows()])
        if tpl_opt != "不使用模板":
            tid = int(tpl_opt.split("ID:")[1].replace(")", ""))
            tpl = tpl_df[tpl_df['id'] == tid].iloc[0]
            st.session_state['generated_email'] = {'subject': tpl['subject'], 'content': tpl['content']}

    # 邮件场景
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

    customer_hook = st.text_input("客户背调钩子（必填）",
        placeholder="例如：看到你们的EN388 Cut D防割面料系列 / 你们专注于工业洗涤耐久的FR工装",
        help="从客户官网/LinkedIn提取1个具体观察点")

    product_focus = st.selectbox("产品切入点（每次只选1个）", [
        "防切割纱线/面料（HPPE/芳纶）",
        "阻燃/耐高温纱线/面料（芳纶1313/1414）",
        "电弧防护面料（IEC 61482）",
        "焊接防护面料（EN ISO 11611）",
        "预氧化丝（PANOX）阻燃材料",
        "多功能复合防护材料"
    ])

    use_ai = bool(st.session_state.get('ai_api_key'))

    if st.button(f"{'🤖 AI智能生成' if use_ai else '✨ 一键生成'}开发信", type="primary"):
        if not customer_hook.strip():
            st.error("请填写客户背调钩子！这是SOP要求的必填项")
            return

        with st.spinner("AI正在根据客户数据和SOP规则撰写开发信..." if use_ai else "正在生成..."):
            if use_ai:
                try:
                    user_prompt = build_user_prompt(customer, mail_type, customer_hook, product_focus)
                    raw = call_claude_api(SYSTEM_PROMPT, user_prompt, st.session_state['ai_api_key'])
                    subject, content = parse_email_response(raw)
                    if not subject:
                        subject = f"Quick question about your protective textiles"
                    if not content or len(content) < 10:
                        content = raw
                except Exception as e:
                    st.error(f"AI调用失败：{str(e)[:200]}")
                    return
            else:
                # 本地模板模式（无 API Key 时的回退）
                name = customer.get('contact_person') or "Sir/Madam"
                company = customer['company_name']
                pfx = product_focus.split('（')[0]
                if '成本' in mail_type:
                    subject = f"10-15% cost cut for your {pfx}"
                    content = f"Hi {name},\n\n{customer_hook}\n\nWe help factories reduce material cost without changing specs.\n\nWould it make sense to compare one of your current items?\n\nBest regards,\n[Your Name]\nKEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd."
                elif '技术' in mail_type:
                    subject = f"{pfx} for your protective textiles"
                    content = f"Hi {name},\n\n{customer_hook}\n\nWe focus on engineered protective yarns and fabrics for industrial PPE, with batch-to-batch consistency and industrial laundering durability.\n\nWorth a short call if you're reviewing materials this quarter?\n\nBest regards,\n[Your Name]\nKEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd."
                elif '贸易' in mail_type:
                    subject = f"Improve margin on {pfx}"
                    content = f"Hi {name},\n\nWe work with European distributors on aramid & HPPE yarn/fabric—often as margin improvement or stable backup supply.\n\nOpen to comparing one SKU when convenient?\n\nBest regards,\n[Your Name]\nKEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd."
                else:
                    subject = f"Re: {pfx} | {company}"
                    content = f"Hi {name},\n\n{customer_hook}\n\nQuick question — are you currently reviewing your {product_focus} supply base?\n\nNo rush, just wanted to check if there's a fit.\n\nBest regards,\n[Your Name]\nKEYSTONE | Jiangsu Kexu Textile Technology Co., Ltd."

            st.session_state['generated_email'] = {"subject": subject, "content": content}

    # 显示生成结果
    if 'generated_email' in st.session_state:
        st.markdown("---")
        label = "📧 AI生成结果（符合SOP：≤5行、纯文本、低压力收尾）" if use_ai else "📧 生成结果（模板模式，配置API Key可启用AI）"
        st.subheader(label)
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
                st.code(f"Subject: {subj}\n\n{cont}", language=None)
                st.success("⬆ 点击上方代码块即可全选复制")
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
