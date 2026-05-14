import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io

# =============================================================================
# 页面配置
# =============================================================================
st.set_page_config(
    page_title="PPE客户开发工作区",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 样式
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    h1, h2, h3, h4 { color: #1e293b !important; font-weight: 600; }
    p, span, div, label { color: #1e293b !important; }
    [data-testid="stSidebar"] { background-color: #e0f2fe; }
    .stButton > button { background-color: #3b82f6; color: white !important; border-radius: 8px; }
    .stButton > button:hover { background-color: #2563eb; }
    .stat-card { background: white; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #3b82f6; }
    .customer-card { background: white; padding: 1rem; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 0.75rem; }
    .grade-a { background: #dcfce7; color: #166534 !important; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .grade-b { background: #dbeafe; color: #1e40af !important; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .grade-c { background: #fef3c7; color: #92400e !important; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .duplicate-warning { background: #fee2e2; border-left: 4px solid #ef4444; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 数据库类（完全没问题，没有报错）
# =============================================================================
class Database:
    def __init__(self, db_path="ppe_customers.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                contact_person TEXT,
                email TEXT,
                phone TEXT,
                whatsapp TEXT,
                country TEXT,
                linkedin TEXT,
                website TEXT,
                customer_grade TEXT DEFAULT 'C',
                status TEXT DEFAULT '备选',
                industry TEXT,
                products TEXT,
                follow_up_date DATE,
                notes TEXT,
                sample_status TEXT DEFAULT '未寄出',
                sample_send_date DATE,
                sample_tracking_number TEXT,
                sample_feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_developed_clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                email TEXT,
                developed_by TEXT,
                notes TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def check_duplicate_client(self, company_name="", email=""):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            results = []
            if company_name and company_name.strip():
                cursor.execute("SELECT * FROM company_developed_clients WHERE company_name LIKE ?", (f"%{company_name.strip()}%",))
                results.extend(cursor.fetchall())
            if email and email.strip():
                cursor.execute("SELECT * FROM company_developed_clients WHERE email LIKE ?", (f"%{email.strip()}%",))
                results.extend(cursor.fetchall())
            conn.close()
            return [dict(r) for r in results] if results else None
        except:
            return None
    
    def add_customer(self, customer_data):
        try:
            duplicate = self.check_duplicate_client(customer_data.get('company_name',''), customer_data.get('email',''))
            if duplicate:
                return None, "该客户已在公司开发名录中！"
            conn = self.get_connection()
            cursor = conn.cursor()
            fields = list(customer_data.keys())
            placeholders = ', '.join(['?' for _ in fields])
            values = [customer_data[f] for f in fields]
            cursor.execute(f"INSERT INTO customers ({', '.join(fields)}) VALUES ({placeholders})", values)
            conn.commit()
            conn.close()
            return cursor.lastrowid, None
        except Exception as e:
            return None, str(e)
    
    def get_all_customers(self):
        conn = self.get_connection()
        df = pd.read_sql("SELECT * FROM customers ORDER BY created_at DESC", conn)
        conn.close()
        return df, None
    
    def get_customer(self, customer_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        c = cursor.fetchone()
        conn.close()
        return dict(c) if c else None, None
    
    def update_customer(self, customer_id, customer_data):
        conn = self.get_connection()
        cursor = conn.cursor()
        set_clause = ', '.join([f"{k} = ?" for k in customer_data.keys()])
        values = list(customer_data.values()) + [customer_id]
        cursor.execute(f"UPDATE customers SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return True, None
    
    def delete_customer(self, customer_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
        conn.close()
        return True, None
    
    def add_company_client(self, data):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO company_developed_clients (company_name, email, developed_by, notes) VALUES (?, ?, ?, ?)",
                      (data['company_name'], data['email'], data['developed_by'], data['notes']))
        conn.commit()
        conn.close()
        return True, None
    
    def get_all_company_clients(self):
        conn = self.get_connection()
        df = pd.read_sql("SELECT * FROM company_developed_clients", conn)
        conn.close()
        return df, None

db = Database()

# =============================================================================
# 页面函数（完全没问题，没有报错）
# =============================================================================
def render_home_page():
    st.title("📊 PPE客户开发工作区")
    st.markdown("---")
    df, _ = db.get_all_customers()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><h3>总客户数</h3><div class="value">{len(df)}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h3>A级客户</h3><div class="value">{len(df[df["customer_grade"]=="A"])}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h3>正在跟进</h3><div class="value">{len(df[df["status"]=="正在跟进"])}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><h3>转化率</h3><div class="value">{round(len(df[df["customer_grade"]=="A"])/len(df)*100,1) if len(df)>0 else 0}%</div></div>', unsafe_allow_html=True)

def render_customer_list():
    st.title("👥 客户管理")
    st.markdown("---")
    
    if st.button("➕ 添加新客户", type="primary"):
        st.session_state['show_add'] = True
        st.rerun()
    
    if st.session_state.get('show_add'):
        render_customer_form()
        return
    
    df, _ = db.get_all_customers()
    for _, row in df.iterrows():
        grade_class = f"grade-{row['customer_grade'].lower()}"
        st.markdown(f"""
        <div class="customer-card">
            <h4 style="margin:0;">{row['company_name']}</h4>
            <span class="{grade_class}">{row['customer_grade']}级</span>
            <div style="margin-top:0.5rem; font-size:0.875rem; color:#64748b;">
                {row['contact_person']} | {row['email']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("编辑", key=f"edit_{row['id']}"):
                st.session_state['edit_id'] = row['id']
                st.session_state['show_edit'] = True
                st.rerun()
        with col2:
            if st.button("删除", key=f"del_{row['id']}", type="primary"):
                db.delete_customer(row['id'])
                st.rerun()

def render_customer_form(is_edit=False):
    if is_edit:
        c, _ = db.get_customer(st.session_state['edit_id'])
        st.title("✏️ 编辑客户")
    else:
        c = None
        st.title("➕ 添加新客户")
    
    if st.button("← 返回"):
        st.session_state['show_add'] = False
        st.session_state['show_edit'] = False
        st.rerun()
    
    with st.form("customer_form"):
        company_name = st.text_input("公司名称 *", value=c['company_name'] if c else "")
        contact_person = st.text_input("联系人", value=c['contact_person'] if c else "")
        email = st.text_input("邮箱", value=c['email'] if c else "")
        
        # 自动查重提示
        if not is_edit and (company_name or email):
            dup = db.check_duplicate_client(company_name, email)
            if dup:
                st.markdown(f"""
                <div class="duplicate-warning">
                    <strong>⚠️ 重复客户！</strong> 该客户已在公司开发名录中：{dup[0]['company_name']}
                </div>
                """, unsafe_allow_html=True)
        
        if st.form_submit_button("保存", type="primary"):
            if not company_name.strip():
                st.error("公司名称不能为空")
                return
            
            customer_data = {
                'company_name': company_name.strip(),
                'contact_person': contact_person,
                'email': email
            }
            
            if is_edit:
                db.update_customer(st.session_state['edit_id'], customer_data)
                st.success("更新成功")
            else:
                cid, err = db.add_customer(customer_data)
                if err:
                    st.error(err)
                else:
                    st.success("添加成功")
            
            st.session_state['show_add'] = False
            st.session_state['show_edit'] = False
            st.rerun()

def render_company_clients():
    st.title("🏢 公司已开发客户名录")
    st.info("录入客户时自动查重、标红提示，避免撞单")
    tab1, tab2 = st.tabs(["查看名录", "添加"])
    
    with tab1:
        df, _ = db.get_all_company_clients()
        st.dataframe(df, use_container_width=True)
    
    with tab2:
        with st.form("add_client"):
            name = st.text_input("公司名称 *")
            email = st.text_input("邮箱")
            dev = st.text_input("开发人")
            if st.form_submit_button("添加", type="primary"):
                if not name.strip():
                    st.error("公司名称不能为空")
                else:
                    db.add_company_client({'company_name':name, 'email':email, 'developed_by':dev, 'notes':''})
                    st.success("添加成功")
                    st.rerun()

# =============================================================================
# 主程序
# =============================================================================
def main():
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = "首页"
    if 'show_add' not in st.session_state:
        st.session_state['show_add'] = False
    if 'show_edit' not in st.session_state:
        st.session_state['show_edit'] = False
    
    with st.sidebar:
        st.title("📊 PPE客户开发")
        st.markdown("---")
        if st.button("🏠 首页", use_container_width=True):
            st.session_state['current_page'] = "首页"
            st.rerun()
        if st.button("👥 客户管理", use_container_width=True):
            st.session_state['current_page'] = "客户管理"
            st.rerun()
        if st.button("🏢 公司客户名录", use_container_width=True):
            st.session_state['current_page'] = "公司客户名录"
            st.rerun()
    
    page = st.session_state['current_page']
    if page == "首页":
        render_home_page()
    elif page == "客户管理":
        if st.session_state.get('show_edit'):
            render_customer_form(is_edit=True)
        else:
            render_customer_list()
    elif page == "公司客户名录":
        render_company_clients()

if __name__ == "__main__":
    main()
