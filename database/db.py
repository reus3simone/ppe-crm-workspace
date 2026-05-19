import sqlite3
import re
import os
import pandas as pd
from datetime import datetime, timedelta, date

class Database:
    def __init__(self):
        self.db_path = "ppe_customers.db"
        self._ready = False
        self._init_error = None
        self._ensure_ready()

    def _ensure_ready(self):
        if self._ready:
            return
        if self._init_error:
            raise Exception(self._init_error)
        try:
            self.init_database()
            self._ready = True
        except Exception as e:
            self._init_error = str(e)
            raise

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

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS co_worker_customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    co_worker_name TEXT NOT NULL,
                    company_name TEXT,
                    contact_person TEXT,
                    email TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS team_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 默认团队成员
            default_members = ['Elsa', '张三', '李四']
            for name in default_members:
                cursor.execute("""
                    INSERT OR IGNORE INTO team_members (name) VALUES (?)
                """, (name,))

            default_settings = {
                'company_intro': """KEYSTONE is the international brand of Jiangsu Kexu Textile Technology Co., Ltd. (est. 2000, Changzhou, China).
We engineer staple-fiber protective yarns and fabrics for industrial PPE—cut resistance, FR / heat protection, and arc-related protective textiles—with in-house yarn spinning and fabric engineering capabilities.""",
                'ai_email_prompt': """常州科旭纺织开发信核心规则（SOP V3）：
1. 第一封唯一目标：不被删 + 专业感 + 同行感
2. 正文≤5行，短、克制、纯文本
3. 只讲1个观察点或1个痛点
4. 低压力收尾，给客户退路
5. 禁用套话：We are a professional manufacturer...
6. 禁用：Best price、Leading supplier
7. 第一封无附件、无链接、无PDF
8. 标题像同事往来，含客户业务关键词
9. 发送纪律：当地工作日09:30-10:30，周二至周四优先，每天≤20封，间隔≥5分钟
10. 禁用：offer/discount/supplier/best price在标题中""",
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
                existing_grade = str(row_dict.get('customer_grade', '')).strip()
                if existing_grade and existing_grade not in ('A', 'B', 'C', ''):
                    conn.execute("UPDATE customers SET auto_score = ? WHERE id = ?", (score, row['id']))
                elif not existing_grade or existing_grade in ('A', 'B', 'C'):
                    grade = self._get_customer_grade_by_score(score)
                    conn.execute("UPDATE customers SET auto_score = ?, customer_grade = ? WHERE id = ?", (score, grade, row['id']))
                else:
                    conn.execute("UPDATE customers SET auto_score = ? WHERE id = ?", (score, row['id']))
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
                'customer_grade', 'last_follow_up_date', 'assigned_to', 'status'
            ]

            score = self._calculate_auto_score(customer_data)
            customer_data['auto_score'] = score
            manual_grade = customer_data.get('customer_grade', '').strip()
            if manual_grade not in ('A', 'B', 'C'):
                customer_data['customer_grade'] = self._get_customer_grade_by_score(score)
            if 'last_follow_up_date' not in customer_data or not customer_data.get('last_follow_up_date'):
                customer_data['last_follow_up_date'] = datetime.now().strftime('%Y-%m-%d')
            customer_data.setdefault('assigned_to', 'Elsa')
            customer_data.setdefault('status', '正在跟进')

            clean_data = {k: customer_data.get(k, '') for k in fixed_fields}

            conn = self.get_connection()
            cursor = conn.cursor()
            fields = list(clean_data.keys())
            placeholders = ', '.join(['?' for _ in fields])
            values = [clean_data[f] for f in fields]

            query = f"INSERT INTO customers ({', '.join(fields)}) VALUES ({placeholders})"
            cursor.execute(query, values)
            customer_id = cursor.lastrowid

            # ===== 修 bug：如果导入的开发进度已表明发过信，自动补 timeline =====
            dev_status = str(clean_data.get('development_status', '')).strip()
            is_sent = (
                dev_status in ('已报价', '样品阶段', '已成交')
                or '已发' in dev_status and '开发信' in dev_status
                or '已发' in dev_status and '邮件' in dev_status
            )
            if is_sent:
                cursor.execute("""
                    INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                    VALUES (?, ?, ?)
                """, (customer_id, "生成邮件",
                      f"导入标记：客户在表格中已标注为「{dev_status}」，跳过首轮开发"))
                cursor.execute("""
                    UPDATE customers SET last_follow_up_date = ? WHERE id = ?
                """, (datetime.now().strftime('%Y-%m-%d'), customer_id))

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

            # 保护检查
            try:
                p_warns = self.check_protection_conflict(
                    clean_data.get('company_name', ''),
                    clean_data.get('contact_person', ''),
                    clean_data.get('email', '')
                )
                if p_warns:
                    for pw in p_warns:
                        cursor.execute("""
                            INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                            VALUES (?, ?, ?)
                        """, (customer_id, "撞客户警告", pw['message']))
            except Exception:
                pass

            conn.commit()
            conn.close()
            return customer_id, conflicts
        except Exception as e:
            return None, str(e)

    def _parse_contacts(self, raw_text):
        """从联系方式字段中提取邮箱、电话、联系人姓名，返回 (email, phone, contact_person)"""
        email, phone, person = '', '', ''
        if not raw_text or not str(raw_text).strip():
            return email, phone, person
        text = str(raw_text).strip()

        # 提取邮箱
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if email_match:
            email = email_match.group(0).strip()

        # 提取电话号码
        phone_match = re.search(r'(?:(?:Tel|电话|Phone)[.:]*\s*)?(\+?\d{1,4}[\s-]?\d{2,5}[\s-]?\d{3,5}[\s-]?\d{2,4}(?:[\s-]?\d{2,5})?)', text)
        if phone_match:
            phone = phone_match.group(1).strip()

        # 提取联系人姓名
        name_char = r'[A-ZÀ-ɏ][-a-zA-ZÀ-ɏ]+'
        m1 = re.search(r'(?:Mr\.?|Ms\.?|Mrs\.?)\s+(' + name_char + r'(?:\s+' + name_char + r'){1,2})', text)
        if m1:
            person = m1.group(1).strip()
        else:
            m2 = re.search(r'(' + name_char + r'\s+' + name_char + r')\s*[|（(]', text)
            if m2:
                candidate = m2.group(1).strip()
                if candidate.lower() not in ('purchasing department', 'managing director',
                    'director marketing', 'technical director', 'general manager',
                    'import department', 'sales department', 'all rights', 'sungin tex'):
                    person = candidate
            if not person:
                m3 = re.search(r'(' + name_char + r'(?:\s+' + name_char + r'){1,2})', text)
                if m3:
                    candidate = m3.group(1).strip()
                    if candidate.lower() not in ('purchasing department', 'managing director',
                        'director marketing', 'technical director', 'general manager',
                        'import department', 'sales department', 'sungin tex',
                        'edk vina', 'company limited', 'all rights'):
                        person = candidate

        stop_words = {'info', 'sales', 'marketing', 'procurement', 'import', 'sekretariat',
                      'admin', 'office', 'export', 'contact', 'purchasing', 'managing',
                      'director', 'general', 'technical', 'sungin', 'all rights'}
        if person.lower() in stop_words:
            person = ''

        def clean(s):
            s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
            s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            return re.sub(r'\s+', ' ', s).strip()

        return clean(email), clean(phone), clean(person)

    def batch_import_customers(self, df):
        """批量导入客户，自动识别表格字段映射。返回 (成功数, 重复数, 失败数, 错误信息)"""
        col_map = {
            '公司': 'company_name', '公司名称': 'company_name',
            '国家': 'country',
            '公司定位': 'industry',
            '业务对接': 'products',
            '联系方式': '_contacts_raw',
            '开发进度': 'development_status',
            '客户意向': 'customer_grade',
            '客户等级': 'customer_grade',
            '备注': 'notes',
        }

        direct_fields = ['company_name', 'contact_person', 'email', 'phone', 'country',
                         'linkedin', 'website', 'products', 'notes', 'customer_grade',
                         'status', 'whatsapp', 'industry', 'development_status', 'source']

        success_count = 0
        duplicate_count = 0
        error_count = 0
        first_error = None

        def clean_text(val):
            if not val:
                return ''
            s = str(val)
            s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
            s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            return re.sub(r'\s+', ' ', s).strip()

        for _, row in df.iterrows():
            data = {}
            has_mapped = False

            for excel_col, crm_field in col_map.items():
                if excel_col in df.columns and pd.notna(row[excel_col]):
                    raw_val = clean_text(row[excel_col])
                    if crm_field == '_contacts_raw':
                        email, phone, person = self._parse_contacts(raw_val)
                        data['email'] = email
                        data['phone'] = phone
                        if person:
                            data['contact_person'] = person
                        has_mapped = True
                    elif crm_field == 'notes':
                        if not raw_val.startswith('=DISPIMG'):
                            data[crm_field] = raw_val
                        has_mapped = True
                    else:
                        data[crm_field] = raw_val
                        has_mapped = True

            if not has_mapped:
                for field in direct_fields:
                    if field in df.columns and pd.notna(row[field]):
                        data[field] = str(row[field]).strip()

            company = data.get('company_name', '')
            if not company or any(kw in company for kw in ['日开发完', '开发完第', '------', '=====', '小计']):
                continue

            data.setdefault('development_status', '初次开发')
            data.setdefault('status', '正在跟进')

            cid, result = self.add_customer(data)
            if cid:
                success_count += 1
            elif result and isinstance(result, str) and '重复' in result:
                duplicate_count += 1
            else:
                error_count += 1
                if first_error is None and isinstance(result, str):
                    first_error = result
        return success_count, duplicate_count, error_count, first_error

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
                grade_val = customer_data.get('customer_grade', '').strip()
                if grade_val not in ('A', 'B', 'C'):
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

    def get_customer_follow_up_stats(self, customer_id):
        """获取客户跟进统计"""
        try:
            tl_df, _ = self.get_customer_timeline(customer_id)
            total = len(tl_df)
            email_count = len(tl_df[tl_df['event_type'] == '生成邮件']) if not tl_df.empty else 0
            research_count = len(tl_df[tl_df['event_type'] == '背调完成']) if not tl_df.empty else 0
            last_contact = None
            if not tl_df.empty:
                try:
                    last_contact = pd.to_datetime(tl_df.iloc[0]['created_at'])
                except Exception:
                    pass
            fc = tl_df[tl_df['event_type'] == '跟进邮件'].shape[0] if not tl_df.empty else 0
            return {
                'total_events': total, 'email_count': email_count,
                'research_count': research_count, 'follow_up_count': fc,
                'last_contact': last_contact,
            }, None
        except Exception as e:
            return None, str(e)

    def get_all_customers_with_stats(self):
        """获取所有客户并附带跟进次数和最后活动时间"""
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM customers ORDER BY created_at DESC", conn)
            if df.empty:
                conn.close()
                return df, None
            stats_df = pd.read_sql("""
                SELECT customer_id, COUNT(*) as event_count,
                       MAX(created_at) as last_event_time
                FROM follow_up_timeline GROUP BY customer_id
            """, conn)
            conn.close()
            df = df.merge(stats_df, left_on='id', right_on='customer_id', how='left')
            df['event_count'] = df['event_count'].fillna(0).astype(int)
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    def get_customer_health(self, last_follow_up_date):
        """根据最后跟进日期判断健康度"""
        if not last_follow_up_date or (isinstance(last_follow_up_date, float) and pd.isna(last_follow_up_date)):
            return {'status': 'new', 'label': '新客户', 'icon': '🆕', 'color': '#6b7280'}
        try:
            last = pd.to_datetime(last_follow_up_date).date()
            days = (datetime.now().date() - last).days
        except Exception:
            return {'status': 'unknown', 'label': '未知', 'icon': '❓', 'color': '#6b7280'}
        if days <= 7:
            return {'status': 'active', 'label': '活跃', 'icon': '🟢', 'color': '#22c55e'}
        elif days <= 14:
            return {'status': 'cooling', 'label': '变凉', 'icon': '🟡', 'color': '#eab308'}
        elif days <= 60:
            return {'status': 'danger', 'label': '危险', 'icon': '🔴', 'color': '#ef4444'}
        else:
            return {'status': 'dormant', 'label': '沉睡', 'icon': '⚫', 'color': '#6b7280'}

    def get_global_activity_feed(self, limit=30):
        """全局活动流：所有客户的最新动态"""
        try:
            conn = self.get_connection()
            df = pd.read_sql(f"""
                SELECT t.*, c.company_name, c.country, c.customer_grade
                FROM follow_up_timeline t
                LEFT JOIN customers c ON t.customer_id = c.id
                WHERE c.id IS NOT NULL
                ORDER BY t.created_at DESC LIMIT ?
            """, conn, params=(limit,))
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    _PRODUCT_RULES = [
        ('阻燃面料（FR protective fabrics）', '⭐ 优先',
         ['fr fabric', '阻燃面料', 'flame retardant fabric', 'fire retardant',
          'nfpa 2112', 'en iso 11612', 'en11612',
          'arc flash', '电弧', '电弧防护', '焊接', 'welding', 'en iso 11611',
          '工装面料', 'workwear fabric', 'firefighter', '消防服',
          '防护服面料', '阻燃工装', 'fr clothing',
          '热防护', 'thermal protective', '高温防护']),
        ('防切割面料（Cut-resistant fabrics）', '⭐ 优先',
         ['cut resistant fabric', '防切割面料', '防割面料', 'en388',
          'ansi cut', 'protective fabric', '防护面料',
          '抗切割', '耐磨面料', 'anti cut', 'cut resistant textile',
          '高强面料', 'high strength fabric']),
        ('防切割纱线（Cut-resistant yarns）', '⭐ 优先',
         ['cut resistant yarn', '防切割纱线', 'hppe yarn', '芳纶纱',
          '针织纱', '手套纱', 'knitting yarn', 'glove yarn',
          '包芯纱', 'core spun', '复合纱', 'composite yarn',
          '防割纱', '抗切割纱线']),
        ('阻燃耐高温纱线（FR / aramid yarns）', '高',
         ['fr yarn', '阻燃纱线', '耐高温纱线', 'heat resistant yarn',
          '芳纶', 'aramid', 'meta-aramid', '间位芳纶', '1313',
          '对位芳纶', '1414', 'para-aramid',
          '预氧丝', 'panox', '预氧化', '氧化丝',
          '改性腈纶', 'modacrylic', '阻燃腈纶',
          '混纺纱', '阻燃混纺', 'fr blended']),
        ('防切割手套（Cut-resistant gloves）', '中',
         ['手套', 'glove', 'hand protection', '护具', 'knitted glove',
          '机械防护', '作业防护', '劳保手套', '安全手套',
          '防割手套', 'cut resistant glove', 'working glove']),
        ('防割袖套（Cut-resistant sleeves）', '中',
         ['袖套', 'sleeve', 'arm protection', '手臂防护',
          '护袖', 'arm guard', '安全袖套']),
        ('防割服（Cut-resistant clothing）', '中',
         ['防护服', 'protective clothing', 'coverall', '工装', '安全服',
          '防割服', 'cut resistant clothing', '防刺服',
          '抗割服装']),
        ('工业缝纫线（Industrial sewing thread）', '中',
         ['缝纫线', 'sewing thread', 'thread', '阻燃缝纫',
          '芳纶缝纫线', 'aramid thread', '高强缝纫线']),
    ]

    def get_product_match(self, industry, products, notes=""):
        """根据客户行业/产品推荐匹配产品线"""
        text = f"{industry or ''} {products or ''} {notes or ''}".lower()
        if not text.strip():
            return []
        results = []
        for name, priority, keywords in self._PRODUCT_RULES:
            if any(k in text for k in keywords):
                results.append({'product': name, 'priority': priority})
        return results

    _TIMEZONE_MAP = {
        # (base_utc, has_dst, dst_utc, label)
        'germany': (1, True, 2, '德国'), '德国': (1, True, 2, '德国'),
        'france': (1, True, 2, '法国'), '法国': (1, True, 2, '法国'),
        'italy': (1, True, 2, '意大利'), '意大利': (1, True, 2, '意大利'),
        'spain': (1, True, 2, '西班牙'), '西班牙': (1, True, 2, '西班牙'),
        'netherlands': (1, True, 2, '荷兰'), '荷兰': (1, True, 2, '荷兰'),
        'belgium': (1, True, 2, '比利时'), '比利时': (1, True, 2, '比利时'),
        'sweden': (1, True, 2, '瑞典'), '瑞典': (1, True, 2, '瑞典'),
        'norway': (1, True, 2, '挪威'), '挪威': (1, True, 2, '挪威'),
        'finland': (2, True, 3, '芬兰'), '芬兰': (2, True, 3, '芬兰'),
        'denmark': (1, True, 2, '丹麦'), '丹麦': (1, True, 2, '丹麦'),
        'poland': (1, True, 2, '波兰'), '波兰': (1, True, 2, '波兰'),
        'czech': (1, True, 2, '捷克'), '捷克': (1, True, 2, '捷克'),
        'austria': (1, True, 2, '奥地利'), '奥地利': (1, True, 2, '奥地利'),
        'switzerland': (1, True, 2, '瑞士'), '瑞士': (1, True, 2, '瑞士'),
        'uk': (0, True, 1, '英国'), '英国': (0, True, 1, '英国'),
        'portugal': (0, True, 1, '葡萄牙'), '葡萄牙': (0, True, 1, '葡萄牙'),
        'usa': (-5, True, -4, '美国'), '美国': (-5, True, -4, '美国'),
        'united states': (-5, True, -4, '美国'),
        'canada': (-5, True, -4, '加拿大'), '加拿大': (-5, True, -4, '加拿大'),
        'mexico': (-6, False, -6, '墨西哥'), '墨西哥': (-6, False, -6, '墨西哥'),
        'australia': (10, True, 11, '澳大利亚'), '澳大利亚': (10, True, 11, '澳大利亚'),
        'japan': (9, False, 9, '日本'), '日本': (9, False, 9, '日本'),
        'korea': (9, False, 9, '韩国'), '韩国': (9, False, 9, '韩国'),
        'india': (5.5, False, 5.5, '印度'), '印度': (5.5, False, 5.5, '印度'),
        'brazil': (-3, False, -3, '巴西'), '巴西': (-3, False, -3, '巴西'),
        'turkey': (3, False, 3, '土耳其'), '土耳其': (3, False, 3, '土耳其'),
        'russia': (3, False, 3, '俄罗斯'), '俄罗斯': (3, False, 3, '俄罗斯'),
        'colombia': (-5, False, -5, '哥伦比亚'), '哥伦比亚': (-5, False, -5, '哥伦比亚'),
        'vietnam': (7, False, 7, '越南'), '越南': (7, False, 7, '越南'),
    }

    @staticmethod
    def _is_dst_season(today=None):
        """判断当前是否为北半球夏令时季节（3月第2个周日 ~ 11月第1个周日）"""
        if today is None:
            today = date.today()
        # 简化判断：4月~10月为夏令时季节
        return 4 <= today.month <= 10

    def get_timezone_advice(self, country):
        """根据国家获取时区、DST、最佳发送窗口等完整建议"""
        if not country:
            return None
        cl = country.lower().strip()
        matched_key = None
        for key in self._TIMEZONE_MAP:
            if key in cl or cl in key:
                matched_key = key
                break
        if not matched_key:
            if any(eu in cl for eu in ['europe', 'europa']):
                matched_key = 'germany'
            else:
                return None

        base_utc, has_dst, dst_utc, label = self._TIMEZONE_MAP[matched_key]

        today = date.today()
        is_dst = has_dst and self._is_dst_season(today)
        current_utc = dst_utc if is_dst else base_utc

        # 客户当地最佳发送窗口：09:00 - 11:00
        local_start_h, local_end_h = 9, 11

        def _utc_to_cst(utc_offset, local_hour):
            """将客户当地小时转为北京时间"""
            cst_h = (local_hour - utc_offset + 8) % 24
            return int(cst_h)

        cst_start = _utc_to_cst(current_utc, local_start_h)
        cst_end = _utc_to_cst(current_utc, local_end_h)

        # 格式化北京区间
        def _fmt(h):
            return f"{h:02d}:00"

        cst_range = f"{_fmt(cst_start)} - {_fmt(cst_end)}"

        # DST 文字说明
        dst_text = ''
        if has_dst:
            if is_dst:
                dst_text = f'[夏令时] 当前 UTC+{dst_utc}，非夏令时 UTC+{base_utc}（每年3月-10月）'
            else:
                dst_text = f'[冬令时] 当前 UTC+{base_utc}，夏令时 UTC+{dst_utc}（3月-10月）'

        # 客户当地当前时间（近似）
        import datetime as dt
        now_utc = dt.datetime.now(dt.timezone.utc)
        local_now = now_utc.hour + current_utc
        local_now_str = f"{(int(local_now) % 24):02d}:{now_utc.minute:02d}（约）"

        return {
            'utc': current_utc,
            'base_utc': base_utc,
            'is_dst': is_dst,
            'label': label,
            'cst_range': cst_range,
            'local_window': f"{local_start_h}:00 - {local_end_h}:00",
            'dst_text': dst_text,
            'local_now': local_now_str,
        }

    _CULTURE_GUIDE = {
        'germany': {
            'weekend': '周六日',
            'best_days': '周二至周四',
            'avoid_days': '周五下午（很多人提前下班）',
            'language': '德语 / 英语（商务英语可通）',
            'etiquette': [
                '邮件开头用 "Sehr geehrte" + 姓，关系熟后用 "Guten Tag"',
                '德国人重视头衔（Dr./Prof.），称呼别省略',
                '报价要精准、数据要严谨，德国人对模糊表述反感',
                '决策链长且层级分明，不要期望快速成交',
                '见面准时是基本要求，迟到是大忌',
            ],
            'taboos': [
                '别拿二战、纳粹当话题',
                '别跟德国人比价格，他们更看重质量和技术参数',
                '私生活（收入、家庭）不是商务话题',
            ],
            'holidays': '5月： Christi Himmelfahrt（耶稣升天节） | 6月：Pfingsten（圣灵降临节）',
        },
        'france': {
            'weekend': '周六日',
            'best_days': '周二至周四',
            'avoid_days': '周五下午、周一上午、8月全月（全国放假）',
            'language': '法语优先，英语也可',
            'etiquette': [
                '开头用法语问候 "Bonjour" 很重要',
                '法国人重视正式感，邮件不要太随意',
                '8月大部分法国公司关门休假，别在这个月发开发信',
                '商务沟通偏向自上而下，找对决策人比磨中间人有效',
            ],
            'taboos': [
                '别一上来就谈钱，先建立关系',
                '避免英语与法语之间的语言优越感争论',
                '不要在邮件中用过多的销售套话',
            ],
            'holidays': '5月：Fête du Travail（劳动节） | 7/14：国庆日 | 8月：全国暑假',
        },
        'italy': {
            'weekend': '周六日',
            'best_days': '周二至周四',
            'avoid_days': '周五下午、8月 Ferragosto 前后',
            'language': '意大利语 / 英语',
            'etiquette': [
                '意大利人关系导向，先建立信任再谈业务',
                '邮件回复可能不快，不代表没兴趣',
                '八月基本不工作（Ferragosto），别催',
                '意大利中小企业多，老板直接决策',
            ],
            'taboos': [
                '别拿南北差异开玩笑',
                '别跟意大利人比披萨/意面',
                '邮件别太生硬，加点人情味',
            ],
            'holidays': '8月：Ferragosto（全国休假） | 4月：Pasquetta（复活节周一）',
        },
        'spain': {
            'weekend': '周六日',
            'best_days': '周二至周四',
            'avoid_days': '周五下午、8月、Siesta 时间（14:00-16:00）别打电话',
            'language': '西班牙语 / 英语',
            'etiquette': [
                '西班牙也有午休文化，下午2点到4点不适宜打电话',
                '关系建立很重要，初次邮件不要太硬',
                '8月份很多公司关门或不处理新业务',
                '决策比北欧国家慢，正常跟进节奏即可',
            ],
            'taboos': [
                '别问加泰罗尼亚独立等政治话题',
                '别催太紧，西班牙人有自己的节奏',
            ],
            'holidays': '8月：全国暑假 | 各地还有自己的守护神节',
        },
        'uk': {
            'weekend': '周六日',
            'best_days': '周二至周四',
            'avoid_days': '周五下午、Bank Holiday 长周末',
            'language': '英语',
            'etiquette': [
                '英式商务讲究礼貌和保守，不要过于热情',
                '邮件措辞要客气，多用 "please" "I was wondering"',
                '英国人决策偏谨慎，需要多次跟进',
                '善用 "understatement"（低调表达），别过分吹嘘产品',
            ],
            'taboos': [
                '避免谈论脱欧政治话题',
                '不要混淆英国/英格兰/苏格兰的概念',
                '别用美式拼写（color→colour, center→centre）',
                '问工资年龄是粗鲁的',
            ],
            'holidays': '5月：Early May BH / Spring BH | 8月：Summer BH（各地不同）',
        },
        'usa': {
            'weekend': '周六日',
            'best_days': '周一至周四',
            'avoid_days': '周末尽量不打扰、感恩节/圣诞节前后',
            'language': '英语（美式）',
            'etiquette': [
                '美国决策快，直接说明产品价值和差异化优势',
                '美国人喜欢直奔主题，邮件前两行就要抓住注意力',
                '称呼用 First name（名字）即可，不用太正式',
                '感恩节（11月第4个周四）到元旦期间效率低',
            ],
            'taboos': [
                '避免政治话题（大选、枪支、堕胎等）',
                '别过度承诺交付时间',
                '自夸要适度，有数据支撑更好',
            ],
            'holidays': '5月：Memorial Day | 7/4：独立日 | 11月：Thanksgiving | 12月：圣诞+新年',
        },
        'turkey': {
            'weekend': '周六日（周五下午有些公司早退）',
            'best_days': '周日至周四',
            'avoid_days': '周五下午、宗教节日（开斋节/古尔邦节）',
            'language': '土耳其语 / 英语',
            'etiquette': [
                '土耳其人关系导向，信任比价格重要',
                '邮件开头加 "Sayın" + 名字表示尊重',
                '开斋节和古尔邦节前后一周基本不办公',
                '谈判要有耐心，土耳其人喜欢商量',
            ],
            'taboos': [
                '不要批评土耳其的政治或宗教',
                '不要使用与希腊有关的比较',
                '避免左手递名片或物品',
            ],
            'holidays': 'Ramazan Bayrami（开斋节） | Kurban Bayrami（古尔邦节）| 日期每年变动',
        },
        'india': {
            'weekend': '周六日（部分公司周日单休）',
            'best_days': '周一到周五',
            'avoid_days': '排灯节前后、洒红节',
            'language': '英语（印式英语可通）',
            'etiquette': [
                '印度英语口音重，邮件沟通比电话更清晰',
                '印度人习惯讨价还价，报价可以留空间',
                '决策者通常是老板或总监级别',
                '关系建立很重要，先聊几句再谈业务',
            ],
            'taboos': [
                '不要用左手递东西',
                '避免谈巴基斯坦等政治敏感话题',
                '牛在印度是神圣的，别拿牛肉开玩笑',
                '不要催促印度人做决定，他们喜欢多方比较',
            ],
            'holidays': '10-11月：Diwali（排灯节，全国放假）| 3月：Holi（洒红节）',
        },
        'poland': {
            'weekend': '周六日',
            'best_days': '周一至周四',
            'avoid_days': '周五下午、圣诞节/复活节前后',
            'language': '波兰语 / 英语（年轻人英语不错）',
            'etiquette': [
                '波兰商务偏正式，邮件开头用 "Szanowny Pan/Pani" + 姓',
                '报价和条款要写清楚，波兰人注重细节',
                '决策偏慢，需要多轮沟通',
            ],
            'taboos': [
                '不要提俄波关系',
                '别把波兰称为东欧（他们更认同中欧）',
            ],
            'holidays': '5/1：劳动节 | 5/3：宪法日 | Boze Cialo（基督圣体节，日期不定）',
        },
        'portugal': {
            'weekend': '周六日',
            'best_days': '周二至周四',
            'avoid_days': '8月、周五下午、狂欢节前后',
            'language': '葡萄牙语 / 英语',
            'etiquette': [
                '葡国人友好但商务节奏偏慢',
                '建立关系比直接谈价格更有效',
                '8月基本不办公',
            ],
            'taboos': [
                '别拿西班牙和葡萄牙做比较，他们不喜欢被说像西班牙',
                '避免谈论前殖民地话题',
            ],
            'holidays': '6月：Dia de Portugal | 狂欢节（2月）| 8月：全国休假',
        },
        'belgium': {
            'weekend': '周六日',
            'best_days': '周二至周四',
            'avoid_days': '周五下午、7月中旬-8月',
            'language': '荷兰语（弗拉芒）/ 法语 / 英语',
            'etiquette': [
                '比利时分荷语区和法语区，注意对方所在区域',
                '商务偏保守和正式，比法国人更务实',
                '决策偏谨慎，需要耐心跟进',
            ],
            'taboos': [
                '别问客户是弗拉芒人还是瓦隆人（敏感）',
                '避免把比利时和法国混为一谈',
            ],
            'holidays': '7/21：国庆日 | 7-8月：各地暑假',
        },
        'colombia': {
            'weekend': '周六日',
            'best_days': '周二至周四',
            'avoid_days': '周一（很多人周末连休）、周五下午、12月',
            'language': '西班牙语 / 英语（商务英语有限）',
            'etiquette': [
                '哥伦比亚人关系导向，先建立信任',
                '邮件用西班牙语开头更有诚意',
                '决策偏慢，不要催太紧',
            ],
            'taboos': [
                '避免讨论毒品/游击队等敏感话题',
                '12月基本在过节，效率低',
            ],
            'holidays': '12月：圣诞+新年长假',
        },
        'korea': {
            'weekend': '周六日',
            'best_days': '周二至周四',
            'avoid_days': '春节/中秋前后各一周',
            'language': '韩语 / 英语（书面沟通更清晰）',
            'etiquette': [
                '韩国人重视等级和尊重，邮件语气要礼貌正式',
                '决策通常需要上报，不会当场拍板',
                '关系（인맥）很重要，但初次邮件保持专业即可',
                '避免在邮件中过于直接批评或否定',
            ],
            'taboos': [
                '避免谈日本殖民历史',
                '不要在第一次沟通中催促决策',
                '对长辈/上级用敬语，邮件中注意尊重语气',
            ],
            'holidays': '1-2月：Seollal（春节）| 9-10月：Chuseok（中秋）| 日期每年变动',
        },
        'vietnam': {
            'weekend': '周六日',
            'best_days': '周二至周六上午',
            'avoid_days': '春节（Tet）前后两周',
            'language': '越南语 / 英语',
            'etiquette': [
                '越南人关系导向，先建立信任比较好谈',
                '春节（Tet）是最大节日，前后两周不办公',
                '报价可以留余地，越南喜欢友好协商',
            ],
            'taboos': [
                '避免谈中越历史问题',
                '不要公开批评越南政府',
                '送礼要注意分寸，避免让人觉得是贿赂',
            ],
            'holidays': '1-2月：Tet（春节，最重要节日）| 4/30：统一日 | 5/1：劳动节',
        },
    }

    _CN_COUNTRY_MAP = {
        '德国': 'germany', '法国': 'france', '意大利': 'italy',
        '西班牙': 'spain', '英国': 'uk', '荷兰': 'netherlands',
        '比利时': 'belgium', '瑞典': 'sweden', '挪威': 'norway',
        '芬兰': 'finland', '丹麦': 'denmark', '波兰': 'poland',
        '捷克': 'czech', '奥地利': 'austria', '瑞士': 'switzerland',
        '美国': 'usa', '加拿大': 'canada', '墨西哥': 'mexico',
        '澳大利亚': 'australia', '日本': 'japan', '韩国': 'korea',
        '印度': 'india', '巴西': 'brazil', '土耳其': 'turkey',
        '俄罗斯': 'russia', '葡萄牙': 'portugal', '哥伦比亚': 'colombia',
        '越南': 'vietnam',
    }

    def get_cultural_advice(self, country):
        if not country:
            return None
        cl = country.lower().strip()
        # 直接匹配英文键
        for key in self._CULTURE_GUIDE:
            if key in cl or cl in key:
                return self._CULTURE_GUIDE[key]
        # 匹配中文名
        for cn, en in self._CN_COUNTRY_MAP.items():
            if cn in cl or cl in cn:
                return self._CULTURE_GUIDE.get(en)
        return None

    @staticmethod
    def _add_working_days(from_date, days):
        """增加工作日"""
        current = from_date
        added = 0
        while added < days:
            current += timedelta(days=1)
            if current.weekday() < 5:
                added += 1
        return current

    def calculate_next_follow_up(self, customer_id):
        """根据SOP节奏计算下次跟进日期"""
        customer, err = self.get_customer(customer_id)
        if err or not customer:
            return None, err
        tl_df, _ = self.get_customer_timeline(customer_id)
        email_events = tl_df[tl_df['event_type'].isin(['生成邮件', '跟进邮件'])] if not tl_df.empty else pd.DataFrame()
        email_count = len(email_events)
        today = datetime.now().date()
        last_contact = today
        if not tl_df.empty:
            try:
                last_contact = pd.to_datetime(tl_df.iloc[0]['created_at']).date()
            except Exception:
                pass
        if email_count == 0:
            # 兜底：开发进度已标注发过信 → 按首次跟进节奏算
            dev_status = str(customer.get('development_status', '')).strip()
            is_sent = (
                dev_status in ('已报价', '样品阶段', '已成交')
                or '已发' in dev_status and '开发信' in dev_status
                or '已发' in dev_status and '邮件' in dev_status
            )
            if is_sent:
                lfd = customer.get('last_follow_up_date')
                if lfd:
                    try:
                        last_contact = pd.to_datetime(lfd).date()
                    except Exception:
                        pass
                d = self._add_working_days(last_contact, 7)
                return d, f"客户标注为「{dev_status}」，按首次跟进（第1轮），7个工作日后"
            # 真的没发过
            d = self._add_working_days(today, 1)
            return d, "尚未发送开发信，建议尽快发送"
        elif email_count == 1:
            d = self._add_working_days(last_contact, 7)
            return d, f"首次跟进（第{email_count}轮），7个工作日后"
        elif email_count == 2:
            d = self._add_working_days(last_contact, 10)
            return d, f"二次跟进（第{email_count}轮），10个工作日后"
        elif email_count == 3:
            d = self._add_working_days(last_contact, 21)
            return d, f"三次跟进（第{email_count}轮），21个工作日后"
        else:
            return last_contact + timedelta(days=90), "季度轻触达，90天后"

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

    def record_follow_up(self, customer_id, subject, content):
        """记录跟进邮件到历史和时间轴"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM email_history WHERE customer_id = ?", (customer_id,))
            max_v = cursor.fetchone()[0]
            version = (max_v or 0) + 1
            cursor.execute("""
                INSERT INTO email_history (customer_id, version, email_subject, email_content)
                VALUES (?, ?, ?, ?)
            """, (customer_id, version, subject, content))
            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (?, ?, ?)
            """, (customer_id, "跟进邮件", f"跟进邮件 v{version} 已保存"))
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

    # ===== 团队成员管理 =====
    def get_team_members(self):
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM team_members ORDER BY id", conn)
            conn.close()
            return [row['name'] for _, row in df.iterrows()], None
        except Exception as e:
            return [], str(e)

    def add_team_member(self, name):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO team_members (name) VALUES (?)", (name.strip(),))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def remove_team_member(self, name):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM team_members WHERE name = ?", (name,))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    # ===== 撞客户保护名单 =====
    def add_co_worker_customer(self, co_worker_name, company_name='', contact_person='', email='', notes=''):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO co_worker_customers (co_worker_name, company_name, contact_person, email, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (co_worker_name.strip(), company_name.strip(), contact_person.strip(), email.strip(), notes))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def get_co_worker_customers(self):
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM co_worker_customers ORDER BY co_worker_name, id", conn)
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    def delete_co_worker_customer(self, entry_id):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM co_worker_customers WHERE id = ?", (entry_id,))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def check_protection_conflict(self, company_name, contact_person='', email=''):
        """检查新客户是否与团队已有客户撞车，返回所有匹配的警告"""
        if not company_name and not contact_person:
            return []
        df, _ = self.get_co_worker_customers()
        if df.empty:
            return []

        warnings = []
        c_name = str(company_name or '').strip().lower()
        c_person = str(contact_person or '').strip().lower()
        c_email = str(email or '').strip().lower()

        for _, row in df.iterrows():
            level = None
            msg = ''

            r_name = str(row.get('company_name', '') or '').strip().lower()
            r_person = str(row.get('contact_person', '') or '').strip().lower()
            r_email = str(row.get('email', '') or '').strip().lower()
            coworker = row['co_worker_name']

            if c_name and r_name and c_name == r_name:
                level = 'danger'
                msg = f'🔴 公司名与 {coworker} 的客户撞车！该公司已在 {coworker} 名下'
            elif c_person and r_person and c_person == r_person:
                level = 'danger'
                msg = f'🔴 联系人「{contact_person}」与 {coworker} 的客户联系人一致！'
            elif c_email and r_email and c_email == r_email:
                level = 'danger'
                msg = f'🔴 邮箱与 {coworker} 的客户邮箱一致！'

            if level:
                warnings.append({'level': level, 'message': msg, 'co_worker': coworker})

        return warnings

    # ===== 导入时获取 sheet 列表 =====
    def get_excel_sheet_names(self, file_obj):
        """读取 Excel 文件的所有 sheet 名称"""
        try:
            xls = pd.ExcelFile(file_obj)
            return xls.sheet_names, None
        except Exception as e:
            return [], str(e)

    def batch_import_sheet(self, xls, sheet_name):
        """导入指定 sheet，xls 可以是 pd.ExcelFile 对象或文件路径"""
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name)
        except Exception as e:
            return 0, 0, 0, [], str(e)
        # 交给原有的导入逻辑
        return self._batch_import_with_protection(df)

    def _batch_import_with_protection(self, df):
        """导入 DataFrame 并检查每个客户的撞客户风险"""
        # 先正常导入
        s, d, e, err = self.batch_import_customers(df)
        # 再对导入的每行跑保护检查
        all_warnings = []
        for _, row in df.iterrows():
            company = str(row.get('company_name', row.get('公司', '')) or '')
            contact = ''
            email = ''
            # 尝试从原始列中提取
            for c_col in ['contact_person', '联系人']:
                if c_col in df.columns:
                    contact = str(row.get(c_col, '') or '')
                    break
            for e_col in ['email', '联系方式']:
                if e_col in df.columns:
                    raw = str(row.get(e_col, '') or '')
                    if '@' in raw:
                        email = raw
                    break
            if company.strip() or contact.strip() or email.strip():
                try:
                    warns = self.check_protection_conflict(company, contact, email)
                    all_warnings.extend(warns)
                except Exception:
                    pass
        return s, d, e, all_warnings, err

    def get_all_knowledge(self):
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM knowledge_base ORDER BY created_at DESC", conn)
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    def backup_data(self, backup_path):
        """导出所有数据到Excel备份文件（每个表一个sheet）"""
        try:
            conn = self.get_connection()
            os.makedirs(os.path.dirname(backup_path) or '.', exist_ok=True)

            tables = {
                'customers': "SELECT * FROM customers ORDER BY id",
                'email_templates': "SELECT * FROM email_templates ORDER BY id",
                'email_history': "SELECT * FROM email_history ORDER BY id",
                'follow_up_timeline': "SELECT * FROM follow_up_timeline ORDER BY id",
                'system_settings': "SELECT * FROM system_settings ORDER BY id",
            }

            with pd.ExcelWriter(backup_path, engine='openpyxl') as writer:
                for sheet_name, query in tables.items():
                    df = pd.read_sql(query, conn)
                    if df.empty:
                        cursor = conn.cursor()
                        cursor.execute(f"PRAGMA table_info({sheet_name})")
                        columns = [row[1] for row in cursor.fetchall()]
                        pd.DataFrame(columns=columns).to_excel(writer, sheet_name=sheet_name, index=False)
                    else:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def restore_data(self, backup_path):
        """从Excel备份恢复所有数据（全量替换，多sheet）"""
        try:
            xls = pd.ExcelFile(backup_path, engine='openpyxl')
            required_sheets = {'customers', 'email_history', 'follow_up_timeline'}
            missing = required_sheets - set(xls.sheet_names)
            if missing:
                return False, f"备份文件格式无效：缺少sheet {', '.join(sorted(missing))}"

            conn = self.get_connection()
            cursor = conn.cursor()

            customers_df = pd.read_excel(xls, sheet_name='customers')
            email_history_df = pd.read_excel(xls, sheet_name='email_history') if 'email_history' in xls.sheet_names else pd.DataFrame()
            timeline_df = pd.read_excel(xls, sheet_name='follow_up_timeline') if 'follow_up_timeline' in xls.sheet_names else pd.DataFrame()
            templates_df = pd.read_excel(xls, sheet_name='email_templates') if 'email_templates' in xls.sheet_names else pd.DataFrame()
            settings_df = pd.read_excel(xls, sheet_name='system_settings') if 'system_settings' in xls.sheet_names else pd.DataFrame()

            if customers_df.empty:
                return False, "备份文件中「客户」数据为空，无法恢复"

            def get_valid_columns(table_name):
                cursor.execute(f"PRAGMA table_info({table_name})")
                return [row[1] for row in cursor.fetchall()]

            cust_valid = get_valid_columns('customers')
            email_valid = get_valid_columns('email_history')
            timeline_valid = get_valid_columns('follow_up_timeline')
            tpl_valid = get_valid_columns('email_templates')
            settings_valid = get_valid_columns('system_settings')

            cursor.execute("DELETE FROM email_history")
            cursor.execute("DELETE FROM follow_up_timeline")
            cursor.execute("DELETE FROM email_templates")
            cursor.execute("DELETE FROM system_settings")
            cursor.execute("DELETE FROM customers")

            def row_to_dict(row, valid_columns):
                data = {}
                for col in valid_columns:
                    if col in row.index:
                        v = row[col]
                        data[col] = None if pd.isna(v) else (v.item() if hasattr(v, 'item') else v)
                    else:
                        data[col] = None
                return data

            if not settings_df.empty:
                for _, row in settings_df.iterrows():
                    d = row_to_dict(row, settings_valid)
                    key = d.get('setting_key')
                    value = d.get('setting_value')
                    if key:
                        cursor.execute(
                            "INSERT OR REPLACE INTO system_settings (setting_key, setting_value) VALUES (?, ?)",
                            (key, value)
                        )

            if not templates_df.empty:
                for _, row in templates_df.iterrows():
                    d = row_to_dict(row, tpl_valid)
                    name = d.get('name')
                    if not name:
                        continue
                    cursor.execute(
                        "INSERT INTO email_templates (name, category, subject, content) VALUES (?, ?, ?, ?)",
                        (name, d.get('category'), d.get('subject'), d.get('content'))
                    )

            restored_count = 0
            for _, row in customers_df.iterrows():
                d = row_to_dict(row, cust_valid)
                if not str(d.get('company_name', '') or '').strip():
                    continue
                fields = [f for f in cust_valid if f in d]
                values = [d[f] for f in fields]
                placeholders = ', '.join(['?' for _ in fields])
                cursor.execute(
                    f"INSERT INTO customers ({', '.join(fields)}) VALUES ({placeholders})",
                    values
                )
                restored_count += 1

            if not timeline_df.empty:
                for _, row in timeline_df.iterrows():
                    d = row_to_dict(row, timeline_valid)
                    cid = d.get('customer_id')
                    etype = d.get('event_type')
                    if cid is None or not etype:
                        continue
                    cursor.execute(
                        "INSERT INTO follow_up_timeline (customer_id, event_type, event_content) VALUES (?, ?, ?)",
                        (cid, etype, d.get('event_content'))
                    )

            if not email_history_df.empty:
                for _, row in email_history_df.iterrows():
                    d = row_to_dict(row, email_valid)
                    cid = d.get('customer_id')
                    if cid is None:
                        continue
                    cursor.execute(
                        "INSERT INTO email_history (customer_id, version, email_subject, email_content) VALUES (?, ?, ?, ?)",
                        (cid, d.get('version', 1), d.get('email_subject'), d.get('email_content'))
                    )

            conn.commit()
            conn.close()

            parts = [f"客户 {restored_count} 条"]
            restored_emails = len(email_history_df) if not email_history_df.empty else 0
            restored_tl = len(timeline_df) if not timeline_df.empty else 0
            restored_tpls = len(templates_df) if not templates_df.empty else 0
            if restored_emails:
                parts.append(f"邮件 {restored_emails} 条")
            if restored_tl:
                parts.append(f"跟进记录 {restored_tl} 条")
            if restored_tpls:
                parts.append(f"模板 {restored_tpls} 条")

            self._init_all_auto_scores()
            return True, f"恢复完成：{', '.join(parts)}"
        except Exception as e:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            return False, f"恢复失败：{str(e)}"
