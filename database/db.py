import sqlite3
import pandas as pd
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_path="ppe_customers.db"):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            raise Exception(f"数据库连接失败：{str(e)}")

    def init_database(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

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
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    assigned_to TEXT DEFAULT 'Elsa',
                    owner_department TEXT DEFAULT '外贸部',
                    development_status TEXT DEFAULT '初次开发',
                    source TEXT DEFAULT 'Google',
                    last_follow_up_date DATE,
                    auto_score INTEGER DEFAULT 0
                )
            """)

            cursor.execute("PRAGMA table_info(customers)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            new_columns = [
                ('assigned_to', 'TEXT', 'Elsa'),
                ('owner_department', 'TEXT', '外贸部'),
                ('development_status', 'TEXT', '初次开发'),
                ('source', 'TEXT', 'Google'),
                ('last_follow_up_date', 'DATE', None),
                ('auto_score', 'INTEGER', 0)
            ]
            for col, typ, default in new_columns:
                if col not in existing_columns:
                    if default is not None:
                        cursor.execute(f"ALTER TABLE customers ADD COLUMN {col} {typ} DEFAULT '{default}'")
                    else:
                        cursor.execute(f"ALTER TABLE customers ADD COLUMN {col} {typ}")

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

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

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
5. 7个工作日后跟进一次""",
                'protection_days': '30',
                'release_days': '90'
            }

            for key, value in default_settings.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO system_settings (setting_key, setting_value)
                    VALUES (?, ?)
                """, (key, value))

            conn.commit()
            conn.close()
            self._init_all_auto_scores()
        except Exception as e:
            pass

    def _extract_domain(self, email_or_website):
        if not email_or_website:
            return None
        if '@' in email_or_website:
            return email_or_website.split('@')[-1].lower()
        if '://' in email_or_website:
            return email_or_website.split('://')[-1].split('/')[0].lower().replace('www.', '')
        return email_or_website.split('/')[0].lower().replace('www.', '')

    def _calculate_auto_score(self, customer_data):
        score = 0
        products = str(customer_data.get('products', '')).lower()
        industry = str(customer_data.get('industry', '')).lower()
        country = str(customer_data.get('country', '')).lower()
        email = str(customer_data.get('email', ''))
        linkedin = str(customer_data.get('linkedin', ''))

        if any(k in products or k in industry for k in ['ppe', '防护', 'safety', 'protective']):
            score += 20
        if any(k in products or k in industry for k in ['fr', '阻燃', 'flame', 'fire', 'arc', 'welding']):
            score += 20
        eu_countries = ['germany', 'france', 'italy', 'spain', 'uk', 'netherlands', 'belgium', 'sweden', 'norway', 'finland', 'denmark', 'poland', 'czech', 'austria', 'switzerland']
        na_countries = ['usa', 'united states', 'canada', 'mexico']
        if any(c in country for c in eu_countries + na_countries):
            score += 15
        if any(k in products or k in industry for k in ['en ', 'nfpa', 'iec', 'astm', 'iso']):
            score += 15
        if linkedin and linkedin.strip():
            score += 10
        if email and '@' in email and not any(d in email for d in ['gmail', 'hotmail', 'outlook', 'yahoo', '163', 'qq']):
            score += 10
        return score

    def _get_customer_grade_by_score(self, score):
        if score >= 85:
            return 'A'
        elif score >= 60:
            return 'B'
        else:
            return 'C'

    def _init_all_auto_scores(self):
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM customers", conn)
            for _, row in df.iterrows():
                row_dict = dict(row)
                score = self._calculate_auto_score(row_dict)
                grade = self._get_customer_grade_by_score(score)
                conn.execute("UPDATE customers SET auto_score = ?, customer_grade = ? WHERE id = ?", (score, grade, row['id']))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def check_customer_conflict(self, customer_data, exclude_id=None):
        conflicts = []
        conn = self.get_connection()
        query = "SELECT * FROM customers WHERE 1=1"
        params = []
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
        
        df = pd.read_sql(query, conn, params=params)
        conn.close()

        if df.empty:
            return 0, []

        new_company = str(customer_data.get('company_name', '')).strip().lower()
        new_email = str(customer_data.get('email', '')).strip().lower()
        new_website = str(customer_data.get('website', '')).strip().lower()
        new_phone = str(customer_data.get('phone', '')).strip()
        new_whatsapp = str(customer_data.get('whatsapp', '')).strip()
        new_linkedin = str(customer_data.get('linkedin', '')).strip().lower()
        new_domain = self._extract_domain(new_email) or self._extract_domain(new_website)

        for _, existing in df.iterrows():
            existing = dict(existing)
            existing_id = existing['id']
            existing_company = str(existing['company_name']).strip().lower()
            existing_email = str(existing['email']).strip().lower()
            existing_website = str(existing['website']).strip().lower()
            existing_phone = str(existing['phone']).strip()
            existing_whatsapp = str(existing['whatsapp']).strip()
            existing_linkedin = str(existing['linkedin']).strip().lower()
            existing_assigned = existing['assigned_to']
            existing_status = existing['development_status']
            existing_last_follow = existing['last_follow_up_date']

            if new_company and new_company == existing_company:
                return 3, [{
                    'level': 'danger',
                    'message': f"🔴 完全重复！该客户已由 {existing_assigned} 开发",
                    'details': f"客户ID：{existing_id} | 状态：{existing_status} | 最后跟进：{existing_last_follow or '未跟进'}",
                    'customer_id': existing_id
                }]
            if new_email and new_email == existing_email:
                return 3, [{
                    'level': 'danger',
                    'message': f"🔴 完全重复！该邮箱已存在于客户 {existing['company_name']}",
                    'details': f"负责人：{existing_assigned} | 状态：{existing_status}",
                    'customer_id': existing_id
                }]

            if new_domain and new_domain == (self._extract_domain(existing_email) or self._extract_domain(existing_website)):
                conflicts.append({
                    'level': 'warning',
                    'message': f"🟠 高度疑似！域名 {new_domain} 已存在于客户 {existing['company_name']}",
                    'details': f"可能是同一家集团/子公司，建议确认后再继续 | 负责人：{existing_assigned}",
                    'customer_id': existing_id
                })
            if new_website and new_website == existing_website:
                conflicts.append({
                    'level': 'warning',
                    'message': f"🟠 高度疑似！网站相同：{new_website}",
                    'details': f"已存在客户：{existing['company_name']} | 负责人：{existing_assigned}",
                    'customer_id': existing_id
                })
            if new_phone and new_phone == existing_phone:
                conflicts.append({
                    'level': 'info',
                    'message': f"🟡 联系人重复！电话已存在于客户 {existing['company_name']}",
                    'details': f"可能是集团采购或转岗 | 负责人：{existing_assigned}",
                    'customer_id': existing_id
                })
            if new_whatsapp and new_whatsapp == existing_whatsapp:
                conflicts.append({
                    'level': 'info',
                    'message': f"🟡 联系人重复！WhatsApp已存在于客户 {existing['company_name']}",
                    'details': f"可能是集团采购或转岗 | 负责人：{existing_assigned}",
                    'customer_id': existing_id
                })
            if new_linkedin and new_linkedin == existing_linkedin:
                conflicts.append({
                    'level': 'info',
                    'message': f"🟡 联系人重复！LinkedIn已存在于客户 {existing['company_name']}",
                    'details': f"可能是集团采购或转岗 | 负责人：{existing_assigned}",
                    'customer_id': existing_id
                })

        if conflicts:
            return 2, conflicts
        return 0, []

    def check_customer_protection(self, customer_id, current_user='Elsa'):
        customer, err = self.get_customer(customer_id)
        if err or not customer:
            return True, "客户不存在"
        protection_days = int(self.get_setting('protection_days') or 30)
        release_days = int(self.get_setting('release_days') or 90)
        assigned_to = customer['assigned_to']
        last_follow_up = customer['last_follow_up_date']

        if assigned_to == current_user:
            return True, "自己的客户"
        if not assigned_to:
            return True, "客户未分配"
        if last_follow_up:
            try:
                last_date = datetime.strptime(last_follow_up, '%Y-%m-%d').date()
                if (datetime.now().date() - last_date).days > release_days:
                    return True, f"客户已自动释放（{release_days}天无跟进）"
            except Exception:
                pass
        return False, f"客户处于 {assigned_to} 的{protection_days}天保护期内，禁止修改"

    def add_customer(self, customer_data):
        try:
            conflict_level, conflicts = self.check_customer_conflict(customer_data)
            if conflict_level == 3:
                return None, conflicts[0]['message']
            
            fixed_fields = [
                'company_name', 'contact_person', 'email', 'phone', 'whatsapp', 
                'country', 'website', 'linkedin', 'industry', 'products', 
                'source', 'development_status', 'notes', 'auto_score', 
                'customer_grade', 'last_follow_up_date'
            ]
            
            score = self._calculate_auto_score(customer_data)
            customer_data['auto_score'] = score
            customer_data['customer_grade'] = self._get_customer_grade_by_score(score)
            customer_data['last_follow_up_date'] = datetime.now().strftime('%Y-%m-%d')

            clean_data = {k: customer_data.get(k, '') for k in fixed_fields}

            conn = self.get_connection()
            cursor = conn.cursor()
            fields = list(clean_data.keys())
            placeholders = ', '.join(['?' for _ in fields])
            values = [clean_data[f] for f in fields]
            
            query = f"INSERT INTO customers ({', '.join(fields)}) VALUES ({placeholders})"
            cursor.execute(query, values)
            customer_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (?, ?, ?)
            """, (customer_id, "创建客户", f"成功新建客户档案 | 自动评分：{score}分 | 等级：{clean_data['customer_grade']}级"))
            
            if conflicts:
                conflict_msg = "; ".join([c['message'] for c in conflicts])
                cursor.execute("""
                    INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                    VALUES (?, ?, ?)
                """, (customer_id, "冲突提醒", conflict_msg))

            conn.commit()
            conn.close()
            return customer_id, conflicts
        except Exception as e:
            return None, str(e)

    def update_customer(self, customer_id, customer_data, current_user='Elsa'):
        try:
            can_edit, msg = self.check_customer_protection(customer_id, current_user)
            if not can_edit:
                return False, msg
            conflict_level, conflicts = self.check_customer_conflict(customer_data, exclude_id=customer_id)
            if conflict_level == 3:
                return False, conflicts[0]['message']

            existing, _ = self.get_customer(customer_id)
            if existing:
                merged = {**existing, **customer_data}
                score = self._calculate_auto_score(merged)
                customer_data['auto_score'] = score
                customer_data['customer_grade'] = self._get_customer_grade_by_score(score)

            customer_data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = self.get_connection()
            cursor = conn.cursor()
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
            return True, conflicts
        except Exception as e:
            return False, str(e)

    def delete_customer(self, customer_id, current_user='Elsa'):
        try:
            can_edit, msg = self.check_customer_protection(customer_id, current_user)
            if not can_edit:
                return False, msg
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
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM customers ORDER BY created_at DESC", conn)
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    def add_timeline_event(self, customer_id, event_type, event_content):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (?, ?, ?)
            """, (customer_id, event_type, event_content))
            cursor.execute("""
                UPDATE customers SET last_follow_up_date = ? WHERE id = ?
            """, (datetime.now().strftime('%Y-%m-%d'), customer_id))
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
            cursor.execute("""
                UPDATE customers SET last_follow_up_date = ? WHERE id = ?
            """, (datetime.now().strftime('%Y-%m-%d'), customer_id))
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
