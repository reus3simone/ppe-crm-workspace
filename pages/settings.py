import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime
from database.db import Database

db = Database()


def render_settings():
    st.title("⚙️ 设置")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["👥 团队成员", "🛡 撞客户保护名单", "💾 数据备份"])

    with tab1:
        render_team_tab()

    with tab2:
        render_protection_tab()

    with tab3:
        render_backup_tab()


def render_team_tab():
    st.markdown("记录团队成员的姓名，导入/新建客户时会自动比对撞客户。")

    members, err = db.get_team_members()
    if err:
        st.error(err)
        return

    # 显示现有成员
    for m in members:
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f"👤 **{m}**")
        with c2:
            if st.button("移除", key=f"rm_{m}", use_container_width=True):
                db.remove_team_member(m)
                st.rerun()

    # 添加成员
    st.markdown("---")
    with st.form("add_member_form", clear_on_submit=True):
        new_name = st.text_input("新成员姓名", placeholder="输入姓名")
        if st.form_submit_button("➕ 添加", type="primary"):
            if new_name.strip():
                ok, err = db.add_team_member(new_name.strip())
                if ok:
                    st.success(f"已添加 {new_name.strip()}")
                    st.rerun()
                else:
                    st.error(f"添加失败：{err}")
            else:
                st.error("姓名不能为空")


def render_protection_tab():
    st.markdown(
        "在这里录入**同事已开发的客户信息**。导入/新建客户时如果撞公司名、联系人、邮箱，系统会自动红色警告。"
    )
    st.markdown("**至少填一个字段即可**，不用全填。")

    # 添加新条目
    with st.expander("➕ 新增保护条目", expanded=False):
        with st.form("add_protection_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                coworker = st.selectbox(
                    "同事姓名 *",
                    options=db.get_team_members()[0] or ["请先在团队成员中添加"],
                )
                company = st.text_input("公司名", placeholder="选填")
                person = st.text_input("联系人", placeholder="选填")
            with col2:
                email = st.text_input("邮箱", placeholder="选填")
                notes = st.text_area("备注", placeholder="选填")

            submitted = st.form_submit_button("💾 保存", type="primary")
            if submitted:
                if not coworker:
                    st.error("请选择同事姓名")
                elif not company and not person and not email:
                    st.error("公司名、联系人、邮箱至少填一个")
                else:
                    ok, err = db.add_co_worker_customer(coworker, company, person, email, notes)
                    if ok:
                        st.success("已添加")
                        st.rerun()
                    else:
                        st.error(f"失败：{err}")

    # 现有保护名单
    st.markdown("---")
    st.markdown("**现有保护条目**")
    df, err = db.get_co_worker_customers()
    if err:
        st.error(err)
        return

    if df.empty:
        st.info("暂无保护条目")
        return

    for _, row in df.iterrows():
        parts = [f"👤 **{row['co_worker_name']}**"]
        if row.get('company_name'):
            parts.append(f"🏢 {row['company_name']}")
        if row.get('contact_person'):
            parts.append(f"🧑 {row['contact_person']}")
        if row.get('email'):
            parts.append(f"📧 {row['email']}")

        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(" ｜ ".join(parts))
            if row.get('notes'):
                st.markdown(f"<small style='color:#94a3b8;'>{row['notes']}</small>",
                            unsafe_allow_html=True)
        with c2:
            if st.button("删除", key=f"del_prot_{row['id']}", use_container_width=True):
                db.delete_co_worker_customer(row['id'])
                st.rerun()

        st.markdown("---", unsafe_allow_html=True)


def render_backup_tab():
    _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _backup_dir = os.path.join(_base_dir, "assets")
    os.makedirs(_backup_dir, exist_ok=True)

    st.markdown("**备份到服务器（临时存储）**")
    if st.button("📀 手动全量备份", type="primary", use_container_width=False):
        now = datetime.now()
        fname = f"客户备份_{now.strftime('%Y%m%d_%H%M')}.xlsx"
        fpath = os.path.join(_backup_dir, fname)
        ok, err = db.backup_data(fpath)
        if ok:
            st.success(f"✅ 备份成功：{fname}")
            # 清理旧备份
            all_bk = sorted(glob.glob(os.path.join(_backup_dir, "客户备份_*.xlsx")), reverse=True)
            for f in all_bk[5:]:
                try:
                    os.remove(f)
                except Exception:
                    pass
        else:
            st.error(f"❌ 失败：{err}")

    st.markdown("---")
    st.markdown("**下载备份到电脑**")
    backups = sorted(glob.glob(os.path.join(_backup_dir, "客户备份_*.xlsx")), reverse=True)
    if backups:
        sel = st.selectbox("选择备份", [os.path.basename(f) for f in backups])
        fpath = os.path.join(_backup_dir, sel)
        with open(fpath, "rb") as f:
            st.download_button("⬇️ 下载", data=f, file_name=sel,
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("暂无备份，请先点击上方备份按钮")

    st.markdown("---")
    st.markdown("**从备份恢复数据**")
    uploaded = st.file_uploader("选择备份文件", type=['xlsx'])
    if uploaded:
        tmp_path = os.path.join(_backup_dir, "_upload_restore.xlsx")
        with open(tmp_path, "wb") as f:
            f.write(uploaded.getbuffer())
        if st.button("🔄 恢复", type="primary"):
            ok, msg = db.restore_data(tmp_path)
            st.success(f"✅ {msg}" if ok else f"❌ {msg}")
