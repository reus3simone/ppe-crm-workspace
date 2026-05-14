import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import io

# =============================================================================
# 页面配置与主题设置 - 清新浅色主题
# =============================================================================
st.set_page_config(
    page_title="PPE客户开发工作区",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "PPE客户开发管理系统 v3.0"
    }
)

# Streamlit主题配置
st.markdown("""
<style>
    /* 全局背景与文字 */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* 主标题样式 */
    h1, h2, h3, h4 {
        color: #1e293b !important;
        font-weight: 600;
    }
    
    /* 普通文字 */
    p, span, div, label {
        color: #1e293b !important;
    }
    
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background-color: #e0f2fe;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background-color: #e0f2fe;
    }
    
    /* 按钮样式 - 清新蓝色系 */
    .stButton > button {
        background-color: #3b82f6;
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #2563eb;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    
    /* 次要按钮 */
    .stButton > button[kind="secondary"] {
        background-color: #f1f5f9;
        color: #475569 !important;
        border: 1px solid #cbd5e1;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background-color: #e2e8f0;
    }
    
    /* 危险按钮 */
    .stButton > button[kind="primary"] {
        background-color: #ef4444;
        color: white !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #dc2626;
    }
    
    /* 输入框样式 */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select,
    .stDateInput > div > div > input {
        background-color: white;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        color: #1e293b !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* 卡片样式 */
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border-left: 4px solid #3b82f6;
        margin-bottom: 1rem;
    }
    
    .stat-card h3 {
        margin: 0;
        font-size: 0.875rem;
        color: #64748b !important;
        font-weight: 500;
    }
    
    .stat-card .value {
        font-size: 2rem;
        font-weight: 700;
        color: #1e293b !important;
        margin: 0.5rem 0 0 0;
    }
    
    /* 提醒卡片 */
    .reminder-card {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #f59e0b;
        margin-bottom: 0.5rem;
    }
    
    .reminder-card.urgent {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border-left-color: #ef4444;
    }
    
    /* 客户卡片 */
    .customer-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
        margin-bottom: 0.75rem;
        border: 1px solid #e2e8f0;
    }
    
    .customer-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
    }
    
    /* 等级标签 */
    .grade-a {
        background-color: #dcfce7;
        color: #166534 !important;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .grade-b {
        background-color: #dbeafe;
        color: #1e40af !important;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .grade-c {
        background-color: #fef3c7;
        color: #92400e !important;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    /* 状态标签 */
    .status-active {
        background-color: #dcfce7;
        color: #166534 !important;
    }
    
    .status-pending {
        background-color: #fef3c7;
        color: #92400e !important;
    }
    
    .status-rejected {
        background-color: #fee2e2;
        color: #991b1b !important;
    }
    
    /* 样品状态标签 */
    .sample-not-sent {
        background-color: #f1f5f9;
        color: #475569 !important;
    }
    
    .sample-sent {
        background-color: #dbeafe;
        color: #1e40af !important;
    }
    
    .sample-received {
        background-color: #fef3c7;
        color: #92400e !important;
    }
    
    .sample-feedback {
        background-color: #dcfce7;
        color: #166534 !important;
    }
    
    /* 时间轴样式 */
    .timeline-item {
        position: relative;
        padding-left: 2rem;
        padding-bottom: 1.5rem;
        border-left: 2px solid #3b82f6;
    }
    
    .timeline-item:last-child {
        border-left: none;
    }
    
    .timeline-dot {
        position: absolute;
        left: -0.5rem;
        top: 0;
        width: 1rem;
        height: 1rem;
        border-radius: 50%;
        background-color: #3b82f6;
        border: 3px solid white;
        box-shadow: 0 0 0 2px #3b82f6;
    }
    
    .timeline-date {
        font-size: 0.75rem;
        color: #64748b;
        font-weight: 600;
    }
    
    .timeline-content {
        background: white;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        margin-top: 0.25rem;
    }
    
    /* 模板卡片 */
    .template-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        margin-bottom: 0.75rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .template-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
    }
    
    /* 复制成功提示 */
    .copy-success {
        background-color: #dcfce7;
        color: #166534;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin-top: 0.5rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 数据库管理类
# =============================================================================
class Database:
    def __init__(self, db_path="ppe_customers.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """初始化数据库，创建表并执行数据迁移"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. 创建customers表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                contact_person TEXT,
                email TEXT,
                phone TEXT,
                country TEXT,
                linkedin TEXT,
                website TEXT,
                customer_grade TEXT DEFAULT 'C',
                status TEXT DEFAULT '备选',
                industry TEXT,
                products TEXT,
                follow_up_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. 迁移字段
        existing_columns = [col[1] for col in cursor.execute("PRAGMA table_info(customers)").fetchall()]
        if 'sample_status' not in existing_columns:
            cursor.execute("ALTER TABLE customers ADD COLUMN sample_status TEXT DEFAULT '未寄出'")
        if 'sample_send_date' not in existing_columns:
            cursor.execute("ALTER TABLE customers ADD COLUMN sample_send_date DATE")
        if 'sample_tracking_number' not in existing_columns:
            cursor.execute("ALTER TABLE customers ADD COLUMN sample_tracking_number TEXT")
        if 'sample_feedback' not in existing_columns:
            cursor.execute("ALTER TABLE customers ADD COLUMN sample_feedback TEXT")
        if 'whatsapp' not in existing_columns:
            cursor.execute("ALTER TABLE customers ADD COLUMN whatsapp TEXT")
        
        # 3. 邮件历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                version INTEGER NOT NULL,
                email_subject TEXT,
                email_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
            )
        """)
        
        # 4. 知识库表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 5. 系统设置表（AI Prompt配置）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 6. 邮件模板表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                subject TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 7. 跟进时间轴表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS follow_up_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
            )
        """)
        
        # 初始化默认系统设置
        default_settings = {
            'company_intro': """我们是全产业链防护面料工厂，纺纱-织造-后整理一体化。
主营产品：
- 芳纶1313/1414阻燃面料（FRA、AW、PA系列）
- HPPE防切割面料
- PANOX预氧化丝
- 各类工业防护服装面料

所有产品符合EN388、EN469、NFPA 2112等国际标准。""",
            'ai_email_prompt': """你是一名专业的PPE行业外贸业务员，擅长开发欧洲防护客户。
邮件要求：
1. 自然、专业、不模板化
2. 避免强烈的销售感，像行业同行沟通
3. 简短精准，直击痛点
4. 参考公司介绍和客户信息
5. 结尾不要太生硬""",
            'customer_grade_rules': """A级客户标准：
- 有明确的PPE/防护产品线
- 有欧洲/北美市场
- 有相关认证
- 有工业客户群体
- 有研发/技术团队

B级客户标准：
- 有相关产品，但技术属性较弱
- 贸易商/分销商
- 市场范围较小

C级客户标准：
- 产品不匹配
- 只关注价格
- 无明确防护需求""",
            'sop_rules': """开发SOP：
1. 先背调客户网站/LinkedIn
2. 判断客户等级和产品匹配度
3. 找到精准采购切入点
4. 发送个性化开发邮件
5. 3-5天跟进一次"""
        }
        
        for key, value in default_settings.items():
            cursor.execute("""
                INSERT OR IGNORE INTO system_settings (setting_key, setting_value)
                VALUES (?, ?)
            """, (key, value))
        
        conn.commit()
        conn.close()
    
    # =========================================================================
    # 客户CRUD操作
    # =========================================================================
    def add_customer(self, customer_data):
        """添加新客户"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            fields = list(customer_data.keys())
            placeholders = ', '.join(['?' for _ in fields])
            values = [customer_data[f] for f in fields]
            
            query = f"INSERT INTO customers ({', '.join(fields)}) VALUES ({placeholders})"
            cursor.execute(query, values)
            
            customer_id = cursor.lastrowid
            
            # 添加时间轴记录
            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (?, ?, ?)
            """, (customer_id, "创建客户", f"成功创建客户档案"))
            
            conn.commit()
            conn.close()
            return customer_id, None
        except Exception as e:
            return None, str(e)
    
    def batch_import_customers(self, df):
        """批量导入客户"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            success_count = 0
            duplicate_count = 0
            error_count = 0
            
            for _, row in df.iterrows():
                try:
                    # 去重检查（按邮箱或公司名）
                    email = str(row.get('email', '')).strip()
                    company_name = str(row.get('company_name', '')).strip()
                    
                    if email:
                        cursor.execute("SELECT id FROM customers WHERE email = ?", (email,))
                        if cursor.fetchone():
                            duplicate_count += 1
                            continue
                    
                    if company_name:
                        cursor.execute("SELECT id FROM customers WHERE company_name = ?", (company_name,))
                        if cursor.fetchone():
                            duplicate_count += 1
                            continue
                    
                    # 准备数据
                    customer_data = {
                        'company_name': company_name,
                        'contact_person': str(row.get('contact_person', '')),
                        'email': email,
                        'phone': str(row.get('phone', '')),
                        'country': str(row.get('country', '')),
                        'linkedin': str(row.get('linkedin', '')),
                        'website': str(row.get('website', '')),
                        'customer_grade': str(row.get('customer_grade', 'C')),
                        'status': str(row.get('status', '备选')),
                        'industry': str(row.get('industry', '')),
                        'products': str(row.get('products', '')),
                        'notes': str(row.get('notes', ''))
                    }
                    
                    if not customer_data['company_name']:
                        error_count += 1
                        continue
                    
                    fields = list(customer_data.keys())
                    placeholders = ', '.join(['?' for _ in fields])
                    values = [customer_data[f] for f in fields]
                    
                    query = f"INSERT INTO customers ({', '.join(fields)}) VALUES ({placeholders})"
                    cursor.execute(query, values)
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    continue
            
            conn.commit()
            conn.close()
            return success_count, duplicate_count, error_count, None
        except Exception as e:
            return 0, 0, 0, str(e)
    
    def update_customer(self, customer_id, customer_data):
        """更新客户信息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            customer_data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            set_clause = ', '.join([f"{k} = ?" for k in customer_data.keys()])
            values = list(customer_data.values()) + [customer_id]
            
            query = f"UPDATE customers SET {set_clause} WHERE id = ?"
            cursor.execute(query, values)
            
            # 添加时间轴记录
            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (?, ?, ?)
            """, (customer_id, "更新信息", "客户信息已更新"))
            
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)
    
    def delete_customer(self, customer_id):
        """删除客户"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
            cursor.execute("DELETE FROM email_history WHERE customer_id = ?", (customer_id,))
            cursor.execute("DELETE FROM follow_up_timeline WHERE customer_id = ?", (customer_id,))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)
    
    def get_customer(self, customer_id):
        """获取单个客户信息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
            customer = cursor.fetchone()
            conn.close()
            return dict(customer) if customer else None, None
        except Exception as e:
            return None, str(e)
    
    def get_all_customers(self):
        """获取所有客户"""
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM customers ORDER BY created_at DESC", conn)
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)
    
    # =========================================================================
    # 时间轴操作
    # =========================================================================
    def add_timeline_event(self, customer_id, event_type, event_content):
        """添加时间轴事件"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (?, ?, ?)
            """, (customer_id, event_type, event_content))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)
    
    def get_customer_timeline(self, customer_id):
        """获取客户时间轴"""
        try:
            conn = self.get_connection()
            df = pd.read_sql("""
                SELECT * FROM follow_up_timeline 
                WHERE customer_id = ? 
                ORDER BY created_at DESC
            """, conn, params=(customer_id,))
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)
    
    # =========================================================================
    # 邮件历史操作
    # =========================================================================
    def add_email_history(self, customer_id, subject, content):
        """添加邮件历史记录"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT MAX(version) FROM email_history WHERE customer_id = ?", (customer_id,))
            max_version = cursor.fetchone()[0]
            version = (max_version or 0) + 1
            
            cursor.execute("""
                INSERT INTO email_history (customer_id, version, email_subject, email_content)
                VALUES (?, ?, ?, ?)
            """, (customer_id, version, subject, content))
            
            # 添加时间轴记录
            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (?, ?, ?)
            """, (customer_id, "生成邮件", f"开发邮件 v{version} 已生成"))
            
            conn.commit()
            conn.close()
            return version, None
        except Exception as e:
            return None, str(e)
    
    def get_email_history(self, customer_id):
        """获取客户的邮件历史"""
        try:
            conn = self.get_connection()
            df = pd.read_sql("""
                SELECT * FROM email_history 
                WHERE customer_id = ? 
                ORDER BY version DESC
            """, conn, params=(customer_id,))
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)
    
    # =========================================================================
    # 邮件模板操作
    # =========================================================================
    def add_email_template(self, name, category, subject, content):
        """添加邮件模板"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO email_templates (name, category, subject, content)
                VALUES (?, ?, ?, ?)
            """, (name, category, subject, content))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)
    
    def get_all_templates(self):
        """获取所有模板"""
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM email_templates ORDER BY created_at DESC", conn)
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)
    
    def delete_template(self, template_id):
        """删除模板"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM email_templates WHERE id = ?", (template_id,))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)
    
    # =========================================================================
    # 系统设置操作
    # =========================================================================
    def get_setting(self, key):
        """获取系统设置"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = ?", (key,))
            result = cursor.fetchone()
            conn.close()
            return result['setting_value'] if result else ""
        except Exception as e:
            return ""
    
    def update_setting(self, key, value):
        """更新系统设置"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO system_settings (setting_key, setting_value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)
    
    # =========================================================================
    # 知识库操作
    # =========================================================================
    def add_knowledge(self, category, title, content):
        """添加知识库条目"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO knowledge_base (category, title, content)
                VALUES (?, ?, ?)
            """, (category, title, content))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)
    
    def get_all_knowledge(self):
        """获取所有知识库"""
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM knowledge_base ORDER BY created_at DESC", conn)
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

# 初始化数据库
db = Database()

# =============================================================================
# 辅助函数
# =============================================================================
def get_statistics():
    """获取统计数据"""
    df, _ = db.get_all_customers()
    
    if len(df) == 0:
        return {
            'total': 0, 'grade_a': 0, 'grade_b': 0, 'grade_c': 0,
            'status_active': 0, 'status_pending': 0, 'status_rejected': 0,
            'countries': {}, 'conversion_rate': 0
        }
    
    stats = {
        'total': len(df),
        'grade_a': len(df[df['customer_grade'] == 'A']),
        'grade_b': len(df[df['customer_grade'] == 'B']),
        'grade_c': len(df[df['customer_grade'] == 'C']),
        'status_active': len(df[df['status'] == '正在跟进']),
        'status_pending': len(df[df['status'] == '备选']),
        'status_rejected': len(df[df['status'] == '拒绝']),
        'countries': df['country'].value_counts().to_dict(),
        'conversion_rate': round(len(df[df['customer_grade'] == 'A']) / len(df) * 100, 1) if len(df) > 0 else 0
    }
    return stats

def get_follow_up_reminders():
    """获取跟进提醒"""
    df, _ = db.get_all_customers()
    today = datetime.now().date()
    week_end = today + timedelta(days=7)
    
    df['follow_up_date'] = pd.to_datetime(df['follow_up_date']).dt.date
    
    today_follow = df[
        (df['follow_up_date'] == today) & 
        (df['status'] != '拒绝')
    ].sort_values('follow_up_date')
    
    week_follow = df[
        (df['follow_up_date'] > today) & 
        (df['follow_up_date'] <= week_end) & 
        (df['status'] != '拒绝')
    ].sort_values('follow_up_date')
    
    overdue = df[
        (df['follow_up_date'] < today) & 
        (df['status'] != '拒绝') &
        (df['follow_up_date'].notna())
    ].sort_values('follow_up_date')
    
    return {
        'today': today_follow,
        'week': week_follow,
        'overdue': overdue
    }

def render_stat_card(title, value, color="#3b82f6"):
    """渲染统计卡片"""
    st.markdown(f"""
    <div class="stat-card" style="border-left-color: {color};">
        <h3>{title}</h3>
        <div class="value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def render_reminder_customer(row, is_overdue=False):
    """渲染提醒客户卡片"""
    css_class = "reminder-card urgent" if is_overdue else "reminder-card"
    grade_class = f"grade-{row['customer_grade'].lower()}"
    
    st.markdown(f"""
    <div class="{css_class}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>{row['company_name']}</strong>
                <span class="{grade_class}" style="margin-left: 0.5rem;">{row['customer_grade']}级</span>
            </div>
            <small>跟进日期: {row['follow_up_date']}</small>
        </div>
        <div style="margin-top: 0.5rem; font-size: 0.875rem; color: #64748b;">
            {row['contact_person']} | {row['email']}
        </div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# 页面渲染函数
# =============================================================================
def render_home_page():
    """渲染首页 - 数据统计与跟进提醒"""
    st.title("📊 PPE客户开发工作区")
    st.markdown("---")
    
    st.header("📈 数据概览")
    stats = get_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_stat_card("总客户数", stats['total'], "#3b82f6")
    with col2:
        render_stat_card("A级客户", stats['grade_a'], "#10b981")
    with col3:
        render_stat_card("正在跟进", stats['status_active'], "#f59e0b")
    with col4:
        render_stat_card("转化率", f"{stats['conversion_rate']}%", "#8b5cf6")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        render_stat_card("B级客户", stats['grade_b'], "#3b82f6")
    with col2:
        render_stat_card("C级客户", stats['grade_c'], "#f59e0b")
    with col3:
        render_stat_card("已拒绝", stats['status_rejected'], "#ef4444")
    
    # A级客户占比进度条
    st.markdown("---")
    st.subheader("🎯 A级客户占比")
    if stats['total'] > 0:
        st.progress(stats['grade_a'] / stats['total'])
        st.caption(f"A级客户 {stats['grade_a']} / 总客户 {stats['total']}")
    
    st.markdown("---")
    
    reminders = get_follow_up_reminders()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔔 今日需要跟进")
        if len(reminders['overdue']) > 0:
            st.markdown("**⚠️ 已过期的跟进任务:**")
            for _, row in reminders['overdue'].iterrows():
                render_reminder_customer(row, is_overdue=True)
        
        if len(reminders['today']) == 0:
            st.info("今日暂无需要跟进的客户")
        else:
            for _, row in reminders['today'].iterrows():
                render_reminder_customer(row)
    
    with col2:
        st.subheader("📅 本周需要跟进")
        if len(reminders['week']) == 0:
            st.info("本周暂无需要跟进的客户")
        else:
            for _, row in reminders['week'].iterrows():
                render_reminder_customer(row)
    
    st.markdown("---")
    
    st.subheader("🌍 国家分布")
    if stats['countries']:
        country_df = pd.DataFrame({
            '国家': list(stats['countries'].keys()),
            '客户数量': list(stats['countries'].values())
        })
        st.bar_chart(country_df.set_index('国家'), height=300, use_container_width=True)

def render_customer_list():
    """渲染客户列表"""
    st.title("👥 客户管理")
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        search = st.text_input("🔍 搜索客户名称/邮箱")
    with col2:
        grade_filter = st.selectbox("客户等级", ["全部", "A", "B", "C"])
    with col3:
        status_filter = st.selectbox("状态", ["全部", "正在跟进", "备选", "拒绝"])
    with col4:
        if st.button("📥 Excel批量导入", type="primary"):
            st.session_state['show_import'] = True
            st.rerun()
    
    # 批量导入弹窗
    if st.session_state.get('show_import'):
        with st.expander("📥 Excel批量导入客户", expanded=True):
            st.info("支持字段：company_name, contact_person, email, phone, country, linkedin, website, products, notes, customer_grade, status")
            uploaded_file = st.file_uploader("上传Excel文件", type=['xlsx', 'xls'])
            
            if uploaded_file:
                try:
                    df = pd.read_excel(uploaded_file)
                    st.write(f"检测到 {len(df)} 条数据，预览：")
                    st.dataframe(df.head(), use_container_width=True)
                    
                    if st.button("✅ 开始导入", type="primary"):
                        success, duplicate, error, err_msg = db.batch_import_customers(df)
                        if err_msg:
                            st.error(f"导入失败: {err_msg}")
                        else:
                            st.success(f"导入完成！成功: {success} 条，重复: {duplicate} 条，失败: {error} 条")
                            st.session_state['show_import'] = False
                            st.rerun()
                except Exception as e:
                    st.error(f"文件读取失败: {str(e)}")
            
            if st.button("取消"):
                st.session_state['show_import'] = False
                st.rerun()
    
    df, error = db.get_all_customers()
    if error:
        st.error(f"数据库错误: {error}")
        return
    
    if search:
        df = df[df['company_name'].str.contains(search, case=False, na=False) | 
                df['email'].str.contains(search, case=False, na=False)]
    if grade_filter != "全部":
        df = df[df['customer_grade'] == grade_filter]
    if status_filter != "全部":
        df = df[df['status'] == status_filter]
    
    if st.button("➕ 添加新客户", type="primary"):
        st.session_state['show_add_form'] = True
        st.rerun()
    
    st.markdown("---")
    
    if len(df) == 0:
        st.info("暂无客户数据")
        return
    
    for _, row in df.iterrows():
        grade_class = f"grade-{row['customer_grade'].lower()}"
        status_class = f"status-{'active' if row['status'] == '正在跟进' else 'pending' if row['status'] == '备选' else 'rejected'}"
        
        linkedin_link = f'<a href="{row["linkedin"]}" target="_blank">🔗 LinkedIn</a>' if row['linkedin'] and row['linkedin'].strip() else ""
        
        st.markdown(f"""
        <div class="customer-card">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <h4 style="margin: 0;">{row['company_name']}</h4>
                    <div style="margin-top: 0.5rem;">
                        <span class="{grade_class}">{row['customer_grade']}级</span>
                        <span style="margin: 0 0.5rem;" class="{status_class}" style="padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600;">{row['status']}</span>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.875rem; color: #64748b;">{row['country']}</div>
                    {linkedin_link}
                </div>
            </div>
            <div style="margin-top: 0.75rem; font-size: 0.875rem; color: #475569;">
                {row['contact_person']} | {row['email']} | {row['whatsapp'] or row['phone']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
        with col1:
            if st.button("查看详情", key=f"view_{row['id']}"):
                st.session_state['selected_customer'] = row['id']
                st.session_state['current_page'] = "客户详情"
                st.rerun()
        with col2:
            if st.button("编辑", key=f"edit_{row['id']}"):
                st.session_state['edit_customer'] = row['id']
                st.session_state['current_page'] = "编辑客户"
                st.rerun()
        with col3:
            if st.button("删除", key=f"del_{row['id']}", type="primary"):
                success, error = db.delete_customer(row['id'])
                if success:
                    st.success("删除成功")
                else:
                    st.error(f"删除失败: {error}")
                st.rerun()

def render_customer_detail():
    """渲染客户详情页"""
    customer_id = st.session_state.get('selected_customer')
    if not customer_id:
        st.error("请先选择客户")
        return
    
    customer, error = db.get_customer(customer_id)
    if error or not customer:
        st.error(f"获取客户信息失败: {error or '客户不存在'}")
        return
    
    st.title(f"📋 {customer['company_name']}")
    
    if st.button("← 返回列表"):
        st.session_state['current_page'] = "客户列表"
        st.rerun()
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("基本信息")
        st.write(f"**联系人:** {customer['contact_person']}")
        st.write(f"**邮箱:** {customer['email']}")
        st.write(f"**电话:** {customer['phone']}")
        st.write(f"**WhatsApp:** {customer.get('whatsapp', '未填写')}")
        st.write(f"**国家:** {customer['country']}")
        if customer['linkedin'] and customer['linkedin'].strip():
            st.markdown(f"**LinkedIn:** <a href='{customer['linkedin']}' target='_blank'>🔗 打开LinkedIn</a>", unsafe_allow_html=True)
        st.write(f"**网站:** {customer['website']}")
    
    with col2:
        st.subheader("客户状态")
        grade_class = f"grade-{customer['customer_grade'].lower()}"
        st.markdown(f"**客户等级:** <span class='{grade_class}'>{customer['customer_grade']}级</span>", unsafe_allow_html=True)
        st.write(f"**跟进状态:** {customer['status']}")
        st.write(f"**所属行业:** {customer['industry']}")
        st.write(f"**主营产品:** {customer['products']}")
        st.write(f"**下次跟进:** {customer['follow_up_date']}")
    
    st.markdown("---")
    
    st.subheader("📦 样品管理")
    sample_status = customer.get('sample_status', '未寄出')
    sample_status_class = {
        '未寄出': 'sample-not-sent', '已寄出': 'sample-sent', 
        '已收到': 'sample-received', '已反馈': 'sample-feedback'
    }.get(sample_status, 'sample-not-sent')
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**样品状态:** <span class='{sample_status_class}' style='padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.875rem; font-weight: 600;'>{sample_status}</span>", unsafe_allow_html=True)
    with col2:
        st.write(f"**寄出日期:** {customer.get('sample_send_date', '未填写')}")
    with col3:
        st.write(f"**快递单号:** {customer.get('sample_tracking_number', '未填写')}")
    
    if customer.get('sample_feedback'):
        st.write(f"**客户反馈:** {customer['sample_feedback']}")
    
    st.markdown("---")
    
    # 跟进时间轴
    st.subheader("📅 跟进时间轴")
    timeline, _ = db.get_customer_timeline(customer_id)
    if len(timeline) == 0:
        st.info("暂无跟进记录")
    else:
        for _, event in timeline.iterrows():
            st.markdown(f"""
            <div class="timeline-item">
                <div class="timeline-dot"></div>
                <div class="timeline-date">{event['created_at']}</div>
                <div class="timeline-content">
                    <strong>{event['event_type']}</strong><br>
                    {event['event_content']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.subheader("📝 备注信息")
    st.write(customer['notes'] if customer['notes'] else "暂无备注")
    
    st.markdown("---")
    
    st.subheader("📧 邮件历史记录")
    email_history, error = db.get_email_history(customer_id)
    
    if error:
        st.error(f"获取邮件历史失败: {error}")
    elif len(email_history) == 0:
        st.info("暂无邮件历史记录")
    else:
        for _, email in email_history.iterrows():
            with st.expander(f"版本 {email['version']} - {email['created_at']}"):
                st.write(f"**主题:** {email['email_subject']}")
                st.markdown("**内容:**")
                st.markdown(email['email_content'])
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✏️ 编辑客户信息"):
            st.session_state['edit_customer'] = customer_id
            st.session_state['current_page'] = "编辑客户"
            st.rerun()
    with col2:
        if st.button("🤖 AI生成开发邮件"):
            st.session_state['ai_email_customer'] = customer_id
            st.session_state['current_page'] = "AI邮件生成"
            st.rerun()
    with col3:
        if st.button("🔍 客户背景研究"):
            st.session_state['research_customer'] = customer_id
            st.session_state['current_page'] = "客户背景研究"
            st.rerun()

def render_customer_form(is_edit=False):
    """渲染客户添加/编辑表单"""
    if is_edit:
        customer_id = st.session_state.get('edit_customer')
        customer, error = db.get_customer(customer_id)
        if error or not customer:
            st.error("获取客户信息失败")
            return
        st.title("✏️ 编辑客户")
    else:
        customer = None
        st.title("➕ 添加新客户")
    
    if st.button("← 返回"):
        st.session_state['current_page'] = "客户列表"
        if 'show_add_form' in st.session_state:
            del st.session_state['show_add_form']
        st.rerun()
    
    st.markdown("---")
    
    with st.form("customer_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            company_name = st.text_input("公司名称 *", value=customer['company_name'] if customer else "")
            contact_person = st.text_input("联系人", value=customer['contact_person'] if customer else "")
            email = st.text_input("邮箱", value=customer['email'] if customer else "")
            phone = st.text_input("电话", value=customer['phone'] if customer else "")
            whatsapp = st.text_input("WhatsApp", value=customer.get('whatsapp', '') if customer else "")
            country = st.text_input("国家", value=customer['country'] if customer else "")
            linkedin = st.text_input("LinkedIn链接", value=customer['linkedin'] if customer else "")
            website = st.text_input("网站", value=customer['website'] if customer else "")
        
        with col2:
            customer_grade = st.selectbox("客户等级", ["A", "B", "C"], index=["A", "B", "C"].index(customer['customer_grade']) if customer else 2)
            status = st.selectbox("跟进状态", ["正在跟进", "备选", "拒绝"], index=["正在跟进", "备选", "拒绝"].index(customer['status']) if customer else 1)
            industry = st.text_input("所属行业", value=customer['industry'] if customer else "")
            products = st.text_input("主营产品", value=customer['products'] if customer else "")
            follow_up_date = st.date_input("下次跟进日期", value=pd.to_datetime(customer['follow_up_date']).date() if customer and customer['follow_up_date'] else datetime.now().date())
        
        st.markdown("---")
        st.subheader("📦 样品管理")
        col1, col2, col3 = st.columns(3)
        with col1:
            sample_status = st.selectbox("样品状态", ["未寄出", "已寄出", "已收到", "已反馈"], 
                index=["未寄出", "已寄出", "已收到", "已反馈"].index(customer.get('sample_status', '未寄出')) if customer else 0)
        with col2:
            sample_send_date = st.date_input("寄出日期", value=pd.to_datetime(customer.get('sample_send_date')).date() if customer and customer.get('sample_send_date') else datetime.now().date())
        with col3:
            sample_tracking_number = st.text_input("快递单号", value=customer.get('sample_tracking_number', '') if customer else "")
        
        sample_feedback = st.text_area("客户反馈", value=customer.get('sample_feedback', '') if customer else "")
        
        st.markdown("---")
        notes = st.text_area("备注信息", value=customer['notes'] if customer else "")
        
        submitted = st.form_submit_button("💾 保存客户信息", type="primary")
        
        if submitted:
            if not company_name.strip():
                st.error("公司名称不能为空！")
                return
            
            customer_data = {
                'company_name': company_name.strip(),
                'contact_person': contact_person,
                'email': email,
                'phone': phone,
                'whatsapp': whatsapp,
                'country': country,
                'linkedin': linkedin,
                'website': website,
                'customer_grade': customer_grade,
                'status': status,
                'industry': industry,
                'products': products,
                'follow_up_date': follow_up_date.strftime('%Y-%m-%d'),
                'sample_status': sample_status,
                'sample_send_date': sample_send_date.strftime('%Y-%m-%d'),
                'sample_tracking_number': sample_tracking_number,
                'sample_feedback': sample_feedback,
                'notes': notes
            }
            
            if is_edit:
                success, error = db.update_customer(customer_id, customer_data)
                if success:
                    st.success("客户信息更新成功！")
                else:
                    st.error(f"更新失败: {error}")
            else:
                customer_id, error = db.add_customer(customer_data)
                if customer_id:
                    st.success("客户添加成功！")
                else:
                    st.error(f"添加失败: {error}")
            
            st.session_state['current_page'] = "客户列表"
            if 'show_add_form' in st.session_state:
                del st.session_state['show_add_form']
            st.rerun()

def render_ai_email():
    """渲染AI邮件生成页面"""
    customer_id = st.session_state.get('ai_email_customer')
    customer, error = db.get_customer(customer_id) if customer_id else (None, None)
    
    st.title("🤖 AI开发邮件生成")
    
    if st.button("← 返回"):
        st.session_state['current_page'] = "客户详情"
        st.rerun()
    
    st.markdown("---")
    
    if not customer:
        st.error("请先选择客户")
        return
    
    st.info(f"正在为 **{customer['company_name']}** 生成开发邮件")
    
    # 加载系统设置
    company_intro = db.get_setting('company_intro')
    ai_prompt = db.get_setting('ai_email_prompt')
    
    with st.expander("📚 参考公司知识库（自动加载）"):
        st.text_area("公司介绍", value=company_intro, height=150, disabled=True)
        st.text_area("AI生成规则", value=ai_prompt, height=150, disabled=True)
    
    # 模板选择
    templates, _ = db.get_all_templates()
    if len(templates) > 0:
        st.subheader("📑 选择模板")
        template_id = st.selectbox("调用已有模板", ["不使用模板"] + [f"{row['name']} (ID:{row['id']})" for _, row in templates.iterrows()])
        
        if template_id != "不使用模板":
            selected_id = int(template_id.split("ID:")[1].replace(")", ""))
            template = templates[templates['id'] == selected_id].iloc[0]
            st.session_state['generated_email'] = {'subject': template['subject'], 'content': template['content']}
    
    template_type = st.selectbox("邮件类型", [
        "初次开发邮件", "跟进回复邮件", "样品推荐邮件", 
        "节日问候邮件", "新产品推广邮件"
    ])
    
    our_products = st.text_area("我们的产品优势", value=company_intro, height=100)
    
    if st.button("✨ 生成邮件", type="primary"):
        with st.spinner("正在生成邮件..."):
            if template_type == "初次开发邮件":
                subject = f"High Quality PPE Materials - {customer['company_name']}"
                content = f"""Dear {customer['contact_person'] or 'Sir/Madam'},

Hope this email finds you well!

I noticed that {customer['company_name']} is a leading company in the {customer['industry'] or 'PPE'} industry, specializing in {customer['products'] or 'safety products'}.

We are a professional manufacturer of high-performance protective textiles in China.
{our_products}

All our materials comply with international standards. Would you be interested in receiving our catalog or free samples for testing?

Looking forward to your reply!

Best regards,
[Your Name]
Sales Team
"""
            else:
                subject = f"Following up - {customer['company_name']}"
                content = f"""Dear {customer['contact_person'] or 'Sir/Madam'},

Hope you are doing well!

I'm writing to follow up on our previous communication regarding your {customer['products'] or 'PPE material'} needs.

{our_products}

Please let me know if you need any further information.

Best regards,
[Your Name]
"""
            
            st.session_state['generated_email'] = {'subject': subject, 'content': content}
    
    if 'generated_email' in st.session_state:
        email = st.session_state['generated_email']
        
        st.markdown("---")
        st.subheader("📧 生成的邮件")
        
        subject = st.text_input("邮件主题", value=email['subject'])
        content = st.text_area("邮件内容", value=email['content'], height=400)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 保存到邮件历史", type="primary"):
                version, error = db.add_email_history(customer_id, subject, content)
                if version:
                    st.success(f"邮件已保存！版本号: v{version}")
                else:
                    st.error(f"保存失败: {error}")
        with col2:
            if st.button("📋 复制邮件内容"):
                # JS实现复制
                st.markdown(f"""
                <script>
                navigator.clipboard.writeText(`Subject: {subject}\n\n{content}`);
                </script>
                <div class="copy-success">✅ 已复制到剪贴板！</div>
                """, unsafe_allow_html=True)
        with col3:
            if st.button("💾 保存为模板"):
                st.session_state['show_save_template'] = True
        
        if st.session_state.get('show_save_template'):
            with st.form("save_template"):
                template_name = st.text_input("模板名称")
                template_category = st.selectbox("分类", ["开发邮件", "跟进邮件", "样品邮件", "其他"])
                if st.form_submit_button("保存"):
                    success, error = db.add_email_template(template_name, template_category, subject, content)
                    if success:
                        st.success("模板保存成功！")
                        st.session_state['show_save_template'] = False
                        st.rerun()
                    else:
                        st.error(f"保存失败: {error}")

def render_research():
    """渲染客户背景研究页面"""
    customer_id = st.session_state.get('research_customer')
    customer, error = db.get_customer(customer_id) if customer_id else (None, None)
    
    st.title("🔍 客户背景研究")
    
    if st.button("← 返回"):
        st.session_state['current_page'] = "客户详情"
        st.rerun()
    
    st.markdown("---")
    
    if not customer:
        st.error("请先选择客户")
        return
    
    st.subheader(f
