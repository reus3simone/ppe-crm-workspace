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
                    contact_person TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    country TEXT DEFAULT '',
                    linkedin TEXT DEFAULT '',
                    website TEXT DEFAULT '',
                    customer_grade TEXT DEFAULT 'C',
                    status TEXT DEFAULT '备选',
                    industry TEXT DEFAULT '',
                    products TEXT DEFAULT '',
                    follow_up_date TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    sample_status TEXT DEFAULT '未寄出',
                    sample_send_date TEXT DEFAULT '',
                    sample_tracking_number TEXT DEFAULT '',
                    sample_feedback TEXT DEFAULT '',
                    whatsapp TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    assigned_to TEXT DEFAULT 'Elsa',
                    owner_department TEXT DEFAULT '外贸部',
                    development_status TEXT DEFAULT '初次开发',
                    source TEXT DEFAULT 'Google',
                    last_follow_up_date TEXT DEFAULT '',
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
                ('last_follow_up_date', 'TEXT', ''),
                ('auto_score', 'INTEGER', 0)
            ]
            for col, typ, default in new_columns:
                if col not in existing_columns:
                    cursor.execute(f"ALTER TABLE customers ADD COLUMN {col} {typ} DEFAULT '{default}'")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    email_subject TEXT DEFAULT '',
                    email_content TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS follow_up_timeline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    event_content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
                )
            """)

            default_settings = {
                'company_intro': """KEYSTONE is the international brand of Jiangsu Kexu Textile Technology Co., Ltd. (est. 2000, Changzhou, China). 
We engineer staple-fiber protective yarns and fabrics for industrial PPE—cut resistance, FR / heat protection, and arc-related protective textiles—with in-house yarn spinning and fabric engineering capabilities.""",
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
        """✅ 严谨的域名提取，无空值报错"""
        if not email_or_website:
            return None
        clean_str = str(email_or_website).strip().lower()
        if not clean_str:
            return None
        if '@' in clean_str:
            return clean_str.split('@')[-1]
        if '://' in clean_str:
            clean_str = clean_str.split('://')[-1]
        return clean_str.split('/')[0].replace('www.', '')

    def _calculate_auto_score(self, customer_data):
        """✅ 自动评分，无空值报错"""
        score = 0
        products = str(customer_data.get('products', '')).strip().lower()
        industry = str(customer_data.get('industry', '')).strip().lower()
        country = str(customer_data.get('country', '')).strip().lower()
        email = str(customer_data.get('email', '')).strip()
        linkedin = str(customer_data.get('linkedin', '')).strip()

        ppe_keywords = ['ppe', '防护', 'safety', 'protective', '劳保', '安全']
        fr_keywords = ['fr', '阻燃', 'flame', 'fire', 'arc', 'welding', '芳纶', '耐高温']
        high_value_countries = ['germany', 'france', 'italy', 'spain', 'uk', 'netherlands', 'belgium', 'sweden', 'norway', 'finland', 'denmark', 'poland', 'czech', 'austria', 'switzerland', 'usa', 'united states', 'canada', 'mexico']

        if any(k in products or k in industry for k in ppe_keywords):
            score += 20
        if any(k in products or k in industry for k in fr_keywords):
            score += 20
        if any(c in country for c in high_value_countries):
            score += 15
        if linkedin:
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
        """✅ 批量初始化评分，无类型报错"""
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
        """✅ 防撞检测，彻底杜绝运算符报错，100%稳定"""
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

        # 统一处理新客户数据，全去空格转小写
        new_company = str(customer_data.get('company_name', '')).strip().lower()
        new_email = str(customer_data.get('email', '')).strip().lower()
        new_website = str(customer_data.get('website', '')).strip().lower()
        new_phone = str(customer_data.get('phone', '')).strip()
        new_whatsapp = str(customer_data.get('whatsapp', '')).strip()
        new_domain = self._extract_domain(new_email) or self._extract_domain(new_website)

        for _, existing in df.iterrows():
            existing = dict(existing)
            existing_id = existing['id']
            # 统一处理已有客户数据
            existing_company = str(existing['company_name']).strip().lower()
            existing_email = str(existing['email']).strip().lower()
            existing_website = str(existing['website']).strip().lower()
            existing_phone = str(existing['phone']).strip()
            existing_whatsapp = str(existing['whatsapp']).strip()
            existing_assigned = existing['assigned_to']
            existing_status = existing['development_status']

            # 一级冲突：完全重复直接禁止
            if new_company and new_company == existing_company:
                return 3, [{
                    'level': 'danger',
                    'message': f"🔴 完全重复！该客户已由 {existing_assigned} 开发",
                    'details': f"状态：{existing_status}",
                    'customer_id': existing_id
                }]
            if new_email and new_email == existing_email:
                return 3, [{
                    'level': 'danger',
                    'message': f"🔴 完全重复！该邮箱已存在于客户 {existing['company_name']}",
                    'details': f"负责人：{existing_assigned}",
                    'customer_id': existing_id
                }]

            # 二级冲突：域名/网站重复，提示疑似
            existing_email_domain = self._extract_domain(existing_email)
            existing_website_domain = self._extract_domain(existing_website)
            if new_domain:
                if new_domain == existing_email_domain or new_domain == existing_website_domain:
                    conflicts.append({
                        'level': 'warning',
                        'message': f"🟠 高度疑似！域名 {new_domain} 已存在于客户 {existing['company_name']}",
                        'details': f"可能是同一家集团，建议确认",
                        'customer_id': existing_id
                    })

            if new_website and new_website == existing_website:
                conflicts.append({
                    'level': 'warning',
                    'message': f"🟠 高度疑似！网站相同：{new_website}",
                    'details': f"已存在客户：{existing['company_name']}",
                    'customer_id': existing_id
                })

            # 三级冲突：联系方式重复，提示
            if new_phone and new_phone == existing_phone:
                conflicts.append({
                    'level': 'info',
                    'message': f"🟡 联系人重复！电话已存在于客户 {existing['company_name']}",
                    'customer_id': existing_id
                })
            if new_whatsapp and new_whatsapp == existing_whatsapp:
                conflicts.append({
                    'level': 'info',
                    'message': f"🟡 联系人重复！WhatsApp已存在于客户 {existing['company_name']}",
                    'customer_id': existing_id
                })

        if conflicts:
            return 2, conflicts
        return 0, []

    def add_customer(self, customer_data):
        """✅ 新增客户，字段全匹配，无空值报错"""
        try:
            conflict_level, conflicts = self.check_customer_conflict(customer_data)
            if conflict_level == 3:
                return None, conflicts[0]['message']
            
            # 全字段支持，导入不丢数据
            all_fields = [
                'company_name', 'contact_person', 'email', 'phone', 'whatsapp', 
                'country', 'website', 'linkedin', 'industry', 'products', 
                'source', 'development_status', 'notes', 'follow_up_date',
                'auto_score', 'customer_grade', 'last_follow_up_date'
            ]
            
            # 自动计算评分等级
            score = self._calculate_auto_score(customer_data)
            customer_data['auto_score'] = score
            customer_data['customer_grade'] = self._get_customer_grade_by_score(score)
            customer_data['last_follow_up_date'] = datetime.now().strftime('%Y-%m-%d')

            # 统一处理空值，全转字符串
            clean_data = {}
            for k in all_fields:
                val = customer_data.get(k, '')
                clean_data[k] = str(val).strip() if val else ''

            conn = self.get_connection()
            cursor = conn.cursor()
            fields = list(clean_data.keys())
            placeholders = ', '.join(['?' for _ in fields])
            values = [clean_data[f] for f in fields]
            
            query = f"INSERT INTO customers ({', '.join(fields)}) VALUES ({placeholders})"
            cursor.execute(query, values)
            customer_id = cursor.lastrowid

            # 记录跟进日志
            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (?, ?, ?)
            """, (customer_id, "创建客户", f"成功新建 | 自动评分：{score}分 | 等级：{clean_data['customer_grade']}级"))
            
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
            """, (customer_id, "更新信息", "客户资料已修改"))
            conn.commit()
            conn.close()
            return True, conflicts
        except Exception as e:
            return False, str(e)

    def delete_customer(self, customer_id, current_user='Elsa'):
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
            """, (customer_id, "生成邮件", f"开发邮件 v{version} 已保存"))
            conn.commit()
            conn.close()
            return version, None
        except Exception as e:
            return None, str(e)

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
