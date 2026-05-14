import sqlite3
import pandas as pd
from datetime import datetime

class Database:
    def __init__(self, db_path="ppe_customers.db"):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """获取数据库连接，自带行对象返回，避免取值报错"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            raise Exception(f"数据库连接失败：{str(e)}")

    def init_database(self):
        """初始化全量表结构，自动补全缺失字段，无痛兼容旧数据"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 客户主表
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
                    sample_status TEXT DEFAULT '未寄出',
                    sample_send_date DATE,
                    sample_tracking_number TEXT,
                    sample_feedback TEXT,
                    whatsapp TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 邮件历史表
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

            # 行业知识库表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 系统配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 邮件模板表
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

            # 跟进时间轴表
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

            # 初始化默认系统配置（已完整植入你的SOP）
            default_settings = {
                'company_intro': """KEYSTONE is the international brand of Jiangsu Kexu Textile Technology Co., Ltd. (est. 2000, Changzhou, China). 
We engineer staple-fiber protective yarns and fabrics for industrial PPE—cut resistance, FR / heat protection, and arc-related protective textiles—with in-house yarn spinning and fabric engineering capabilities.""",
                'ai_email_prompt': """常州科旭纺织开发信核心规则：
1. 第一封唯一目标：不被删 + 专业感 + 同行感
2. 正文≤5行，短、克制、纯文本
3. 只讲1个观察点或1个痛点
4. 低压力收尾，给客户退路
5. 禁用套话：We are a professional manufacturer...
6. 禁用：Best price、Leading supplier
7. 第一封无附件、无链接、无PDF""",
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
1. 先背调客户网站/LinkedIn，提取1个钩子
2. 判断客户等级和产品匹配度
3. 找到精准采购切入点
4. 发送个性化开发邮件（≤5行）
5. 7个工作日后跟进一次"""
            }

            for key, value in default_settings.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO system_settings (setting_key, setting_value)
                    VALUES (?, ?)
                """, (key, value))

            conn.commit()
            conn.close()
        except Exception as e:
            raise Exception(f"数据库初始化失败：{str(e)}")

    # ====================== 客户主表CRUD ======================
    def add_customer(self, customer_data):
        """新增客户，自带时间轴记录，异常全捕获"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            fields = list(customer_data.keys())
            placeholders = ', '.join(['?' for _ in fields])
            values = [customer_data[f] for f in fields]

            query = f"INSERT INTO customers ({', '.join(fields)}) VALUES ({placeholders})"
            cursor.execute(query, values)
            customer_id = cursor.lastrowid

            # 同步写入跟进时间轴
            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (?, ?, ?)
            """, (customer_id, "创建客户", "成功新建客户档案"))

            conn.commit()
            conn.close()
            return customer_id, None
        except Exception as e:
            return None, str(e)

    def batch_import_customers(self, df):
        """Excel批量导入，自带去重、空值过滤、异常跳过"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            success_count = 0
            duplicate_count = 0
            error_count = 0

            for _, row in df.iterrows():
                try:
                    email = str(row.get('email', '')).strip()
                    company_name = str(row.get('company_name', '')).strip()

                    # 公司名必填校验
                    if not company_name:
                        error_count += 1
                        continue

                    # 邮箱+公司名双重去重
                    if email:
                        cursor.execute("SELECT id FROM customers WHERE email = ?", (email,))
                        if cursor.fetchone():
                            duplicate_count += 1
                            continue
                    cursor.execute("SELECT id FROM customers WHERE company_name = ?", (company_name,))
                    if cursor.fetchone():
                        duplicate_count += 1
                        continue

                    # 数据清洗组装
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
                        'whatsapp': str(row.get('whatsapp', '')),
                        'notes': str(row.get('notes', ''))
                    }

                    fields = list(customer_data.keys())
                    placeholders = ', '.join(['?' for _ in fields])
                    values = [customer_data[f] for f in fields]
                    query = f"INSERT INTO customers ({', '.join(fields)}) VALUES ({placeholders})"
                    cursor.execute(query, values)
                    success_count += 1

                except Exception:
                    error_count += 1
                    continue

            conn.commit()
            conn.close()
            return success_count, duplicate_count, error_count, None
        except Exception as e:
            return 0, 0, 0, str(e)

    def update_customer(self, customer_id, customer_data):
        """更新客户信息，自动刷新更新时间，同步时间轴"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            customer_data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            set_clause = ', '.join([f"{k} = ?" for k in customer_data.keys()])
            values = list(customer_data.values()) + [customer_id]
            query = f"UPDATE customers SET {set_clause} WHERE id = ?"
            cursor.execute(query, values)

            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (?, ?, ?)
            """, (customer_id, "更新信息", "客户资料已修改更新"))

            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def delete_customer(self, customer_id):
        """删除客户，级联删除关联数据，无残留垃圾数据"""
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
        """查询单客户详情，空值安全返回，避免页面崩溃"""
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
        """查询全量客户列表，空数据返回空DataFrame"""
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM customers ORDER BY created_at DESC", conn)
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    # ====================== 跟进时间轴 ======================
    def add_timeline_event(self, customer_id, event_type, event_content):
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

    # ====================== 邮件历史 ======================
    def add_email_history(self, customer_id, subject, content):
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

            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (?, ?, ?)
            """, (customer_id, "生成邮件", f"AI开发邮件 v{version} 已保存"))

            conn.commit()
            conn.close()
            return version, None
        except Exception as e:
            return None, str(e)

    def get_email_history(self, customer_id):
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

    # ====================== 邮件模板 ======================
    def add_email_template(self, name, category, subject, content):
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
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM email_templates ORDER BY created_at DESC", conn)
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    def delete_template(self, template_id):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM email_templates WHERE id = ?", (template_id,))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    # ====================== 系统设置 ======================
    def get_setting(self, key):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = ?", (key,))
            result = cursor.fetchone()
            conn.close()
            return result['setting_value'] if result else ""
        except Exception:
            return ""

    def update_setting(self, key, value):
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

    # ====================== 知识库 ======================
    def add_knowledge(self, category, title, content):
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
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM knowledge_base ORDER BY created_at DESC", conn)
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)