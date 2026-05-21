import streamlit as st
import pandas as pd
from database.db import Database

db = Database()


def render_import_dialog():
    st.markdown("---")
    st.subheader("📥 Excel 批量导入")

    uploaded_file = st.file_uploader("上传 .xlsx / .xls 文件", type=['xlsx', 'xls'])
    if not uploaded_file:
        if st.button("✕ 关闭"):
            st.session_state['ws_show_import'] = False
            st.rerun()
        return

    try:
        xls = pd.ExcelFile(uploaded_file)
    except Exception as e:
        st.error(f"文件解析失败：{e}")
        return

    sheet_names = xls.sheet_names
    st.info(f"该文件包含 {len(sheet_names)} 个 sheet，请勾选要导入的：")

    choices = {}
    for name in sheet_names:
        is_keyword = any(kw in name for kw in ['关键词', 'keyword', 'KEYWORD'])
        choices[name] = st.checkbox(name, value=not is_keyword)

    selected = [n for n, v in choices.items() if v]
    if not selected:
        st.warning("请至少勾选一个 sheet")
        return

    if st.button("✅ 开始导入", type="primary"):
        total_s, total_d, total_e = 0, 0, 0
        all_warnings = []
        progress = st.progress(0)
        status_text = st.empty()

        for i, sheet in enumerate(selected):
            status_text.info(f"正在导入：{sheet}...")
            s, d, e, warns, err = db.batch_import_sheet(xls, sheet)
            total_s += s
            total_d += d
            total_e += e
            all_warnings.extend(warns)
            progress.progress((i + 1) / len(selected))

        if all_warnings:
            for w in all_warnings:
                st.warning(w['message'])

        progress.empty()
        status_text.empty()
        st.success(f"✅ 导入完成｜成功：{total_s} ｜重复跳过：{total_d} ｜失败：{total_e}")

        if st.button("✕ 关闭"):
            st.session_state['ws_show_import'] = False
            st.rerun()
