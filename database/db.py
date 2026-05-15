import os
import re
import pandas as pd
from datetime import datetime, timedelta, date
import psycopg2
import psycopg2.extras


class Database:
    def __init__(self):
        self._ready = False
        self._init_error = None

    def _ensure_ready(self):
        """延迟初始化：第一次调用数据库方法时才建表"""
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

    # ==============================================================
    # 数据库连接（Supabase PostgreSQL）
    # ==============================================================

    def _ensure_ready(self):
        """延迟初始化：第一次调用数据库方法时才建表"""
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

    def _get_config(self):
        """从 Streamlit secrets 或环境变量获取 Supabase 配置"""
        cfg = {}
        try:
            import streamlit as st
            cfg['host'] = st.secrets.get("supabase_host", "")
            cfg['port'] = st.secrets.get("supabase_port", "5432")
            cfg['dbname'] = st.secrets.get("supabase_database", "postgres")
            cfg['user'] = st.secrets.get("supabase_user", "postgres")
            cfg['password'] = st.secrets.get("supabase_password", "")
        except Exception:
            cfg['host'] = os.environ.get("SUPABASE_HOST", "")
            cfg['port'] = os.environ.get("SUPABASE_PORT", "5432")
            cfg['dbname'] = os.environ.get("SUPABASE_DATABASE", "postgres")
            cfg['user'] = os.environ.get("SUPABASE_USER", "postgres")
            cfg['password'] = os.environ.get("SUPABASE_PASSWORD", "")
        return cfg

    def _connect(self):
        """内部：直接创建连接（不触发 init，避免递归）"""
        cfg = self._get_config()
        if not cfg['host'] or not cfg['password']:
            raise Exception(
                "Supabase 未配置！请在 Streamlit Cloud 的 Secrets 中设置：\n\n"
                "supabase_host = \"db.xxx.supabase.co\"\n"
                "supabase_password = \"your-password\"\n\n"
                "其他可选：supabase_port、supabase_database、supabase_user"
            )
        try:
            conn = psycopg2.connect(
                host=cfg['host'],
                port=cfg['port'],
                dbname=cfg['dbname'],
                user=cfg['user'],
                password=cfg['password'],
                sslmode='require'
            )
            conn.cursor_factory = psycopg2.extras.RealDictCursor
            return conn
        except Exception as e:
            raise Exception(f"数据库连接失败：{str(e)}")

    def get_connection(self):
        """对外：获取连接前确保表已建好"""
        self._ensure_ready()
        return self._connect()

    # ==============================================================
    # 初始化建表
    # ==============================================================

    def init_database(self):
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id SERIAL PRIMARY KEY,
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
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    assigned_to TEXT DEFAULT 'Elsa',
                    owner_department TEXT DEFAULT '外贸部',
                    development_status TEXT DEFAULT '初次开发',
                    source TEXT DEFAULT 'Google',
                    last_follow_up_date DATE,
                    auto_score INTEGER DEFAULT 0
                )
            """)

            # 检查并补充缺失列（兼容旧数据迁移）
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'customers' AND table_schema = 'public'
            """)
            existing_cols = {row['column_name'] for row in cursor.fetchall()}

            migrates = [
                ('assigned_to', 'TEXT', "'Elsa'"),
                ('owner_department', 'TEXT', "'外贸部'"),
                ('development_status', 'TEXT', "'初次开发'"),
                ('source', 'TEXT', "'Google'"),
                ('last_follow_up_date', 'DATE', None),
                ('auto_score', 'INTEGER', '0'),
            ]
            for col, typ, default in migrates:
                if col not in existing_cols:
                    if default is not None:
                        cursor.execute(f"ALTER TABLE customers ADD COLUMN IF NOT EXISTS {col} {typ} DEFAULT {default}")
                    else:
                        cursor.execute(f"ALTER TABLE customers ADD COLUMN IF NOT EXISTS {col} {typ}")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_history (
                    id SERIAL PRIMARY KEY,
                    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL,
                    email_subject TEXT,
                    email_content TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id SERIAL PRIMARY KEY,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id SERIAL PRIMARY KEY,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_templates (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT,
                    subject TEXT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS follow_up_timeline (
                    id SERIAL PRIMARY KEY,
                    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    event_content TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

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
                    INSERT INTO system_settings (setting_key, setting_value)
                    VALUES (%s, %s)
                    ON CONFLICT (setting_key) DO NOTHING
                """, (key, value))

            conn.commit()
            conn.close()
            self._init_all_auto_scores()
        except Exception as e:
            raise Exception(f"数据库初始化失败：{str(e)}")

    # ==============================================================
    # 自动评分
    # ==============================================================

    def _extract_domain(self, email_or_website):
        if not email_or_website:
            return None, None
        if '@' in str(email_or_website):
            return str(email_or_website).split('@')[-1].lower(), None
        if '://' in str(email_or_website):
            domain = str(email_or_website).split('://')[-1].split('/')[0].lower().replace('www.', '')
            return None, domain
        return None, str(email_or_website).split('/')[0].lower().replace('www.', '')

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
        eu_na = ['germany', 'france', 'italy', 'spain', 'uk', 'netherlands', 'belgium',
                 'sweden', 'norway', 'finland', 'denmark', 'poland', 'czech', 'austria',
                 'switzerland', 'usa', 'united states', 'canada', 'mexico']
        if any(c in country for c in eu_na):
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
                    conn.execute("UPDATE customers SET auto_score = %s WHERE id = %s", (score, row['id']))
                elif not existing_grade or existing_grade in ('A', 'B', 'C'):
                    grade = self._get_customer_grade_by_score(score)
                    conn.execute("UPDATE customers SET auto_score = %s, customer_grade = %s WHERE id = %s", (score, grade, row['id']))
                else:
                    conn.execute("UPDATE customers SET auto_score = %s WHERE id = %s", (score, row['id']))
            conn.commit()
            conn.close()
        except Exception:
            pass

    # ==============================================================
    # 冲突检测
    # ==============================================================

    def check_customer_conflict(self, customer_data, exclude_id=None):
        conflicts = []
        conn = self.get_connection()
        if exclude_id:
            df = pd.read_sql("SELECT * FROM customers WHERE id != %s", conn, params=(exclude_id,))
        else:
            df = pd.read_sql("SELECT * FROM customers", conn)
        conn.close()

        if df.empty:
            return 0, []

        new_company = str(customer_data.get('company_name', '')).strip().lower()
        new_email = str(customer_data.get('email', '')).strip().lower()
        new_website = str(customer_data.get('website', '')).strip().lower()
        new_phone = str(customer_data.get('phone', '')).strip()
        new_whatsapp = str(customer_data.get('whatsapp', '')).strip()
        new_linkedin = str(customer_data.get('linkedin', '')).strip().lower()
        new_email_domain, new_web_domain = self._extract_domain(new_email or new_website)
        new_domain = new_email_domain or new_web_domain

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

            ex_email_domain, ex_web_domain = self._extract_domain(existing_email or existing_website)
            ex_domain = ex_email_domain or ex_web_domain
            if new_domain and ex_domain and new_domain == ex_domain:
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

    # ==============================================================
    # 客户保护
    # ==============================================================

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
                if isinstance(last_follow_up, str):
                    last_date = datetime.strptime(last_follow_up, '%Y-%m-%d').date()
                else:
                    last_date = last_follow_up
                if (datetime.now().date() - last_date).days > release_days:
                    return True, f"客户已自动释放（{release_days}天无跟进）"
            except Exception:
                pass
        return False, f"客户处于 {assigned_to} 的{protection_days}天保护期内，禁止修改"

    # ==============================================================
    # 客户 CRUD
    # ==============================================================

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
            manual_grade = str(customer_data.get('customer_grade', '')).strip()
            if manual_grade not in ('A', 'B', 'C'):
                customer_data['customer_grade'] = self._get_customer_grade_by_score(score)
            customer_data['last_follow_up_date'] = datetime.now().strftime('%Y-%m-%d')
            customer_data.setdefault('assigned_to', 'Elsa')
            customer_data.setdefault('status', '正在跟进')

            clean_data = {k: customer_data.get(k, '') for k in fixed_fields}

            conn = self.get_connection()
            cursor = conn.cursor()
            fields = list(clean_data.keys())
            placeholders = ', '.join(['%s' for _ in fields])
            values = [clean_data[f] for f in fields]

            query = f"INSERT INTO customers ({', '.join(fields)}) VALUES ({placeholders}) RETURNING id"
            cursor.execute(query, values)
            customer_id = cursor.fetchone()['id']

            # ===== 修 bug：如果开发进度已表明发过信，自动补 timeline =====
            dev_status = str(clean_data.get('development_status', '')).strip()
            if dev_status in ('已发开发信', '已报价', '样品阶段', '已成交'):
                cursor.execute("""
                    INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                    VALUES (%s, %s, %s)
                """, (customer_id, "生成邮件",
                      f"导入标记：客户在表格中已标注为「{dev_status}」，跳过首轮开发"))
                cursor.execute("""
                    UPDATE customers SET last_follow_up_date = %s WHERE id = %s
                """, (datetime.now().strftime('%Y-%m-%d'), customer_id))

            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (%s, %s, %s)
            """, (customer_id, "创建客户", f"成功新建客户档案 | 自动评分：{score}分 | 等级：{clean_data['customer_grade']}级"))

            if conflicts:
                conflict_msg = "; ".join([c['message'] for c in conflicts])
                cursor.execute("""
                    INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                    VALUES (%s, %s, %s)
                """, (customer_id, "冲突提醒", conflict_msg))

            conn.commit()
            conn.close()
            return customer_id, conflicts
        except Exception as e:
            return None, str(e)

    def _parse_contacts(self, raw_text):
        email, phone, person = '', '', ''
        if not raw_text or not str(raw_text).strip():
            return email, phone, person
        text = str(raw_text).strip()

        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if email_match:
            email = email_match.group(0).strip()

        phone_match = re.search(r'(?:(?:Tel|电话|Phone)[.:]*\s*)?(\+?\d{1,4}[\s-]?\d{2,5}[\s-]?\d{3,5}[\s-]?\d{2,4}(?:[\s-]?\d{2,5})?)', text)
        if phone_match:
            phone = phone_match.group(1).strip()

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
                grade_val = str(customer_data.get('customer_grade', '')).strip()
                if grade_val not in ('A', 'B', 'C'):
                    customer_data['customer_grade'] = self._get_customer_grade_by_score(score)

            customer_data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = self.get_connection()
            cursor = conn.cursor()
            set_clause = ', '.join([f"{k} = %s" for k in customer_data.keys()])
            values = list(customer_data.values()) + [customer_id]
            query = f"UPDATE customers SET {set_clause} WHERE id = %s"
            cursor.execute(query, values)
            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (%s, %s, %s)
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
            cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
            cursor.execute("DELETE FROM email_history WHERE customer_id = %s", (customer_id,))
            cursor.execute("DELETE FROM follow_up_timeline WHERE customer_id = %s", (customer_id,))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def get_customer(self, customer_id):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
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

    # ==============================================================
    # 时间轴 & 跟进
    # ==============================================================

    def add_timeline_event(self, customer_id, event_type, event_content):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (%s, %s, %s)
            """, (customer_id, event_type, event_content))
            cursor.execute("""
                UPDATE customers SET last_follow_up_date = %s WHERE id = %s
            """, (datetime.now().strftime('%Y-%m-%d'), customer_id))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    # ==============================================================
    # 跟进统计 & 健康度
    # ==============================================================

    def get_customer_follow_up_stats(self, customer_id):
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
        try:
            conn = self.get_connection()
            df = pd.read_sql(f"""
                SELECT t.*, c.company_name, c.country, c.customer_grade
                FROM follow_up_timeline t
                LEFT JOIN customers c ON t.customer_id = c.id
                WHERE c.id IS NOT NULL
                ORDER BY t.created_at DESC LIMIT %s
            """, conn, params=(limit,))
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    # ==============================================================
    # 产品匹配
    # ==============================================================

    _PRODUCT_RULES = [
        ('阻燃面料（FR protective fabrics）', '⭐ 优先',
         ['fr', '阻燃', 'flame', 'fire retardant', 'nfpa 2112', 'en iso 11612',
          'arc flash', '电弧', '焊接', 'welding', 'en iso 11611', '工装',
          'workwear', 'firefighter', '消防', '防护服']),
        ('防切割面料（Cut-resistant fabrics）', '⭐ 优先',
         ['cut resistant fabric', '防切割面料', '防割面料', 'en388',
          'ansi cut', 'protective fabric', '防护面料']),
        ('防切割纱线（Cut-resistant yarns）', '⭐ 优先',
         ['cut resistant yarn', '防切割纱线', 'hppe yarn', '芳纶纱',
          '针织纱', '手套纱', 'knitting yarn', 'glove yarn']),
        ('阻燃耐高温纱线（FR / aramid yarns）', '高',
         ['fr yarn', '阻燃纱线', '耐高温纱线', 'heat resistant yarn',
          '芳纶', 'aramid', 'meta-aramid', '预氧丝', 'panox']),
        ('防切割手套（Cut-resistant gloves）', '中',
         ['手套', 'glove', 'hand protection', '护具', 'knitted glove',
          '机械防护', '作业防护']),
        ('防割袖套（Cut-resistant sleeves）', '中',
         ['袖套', 'sleeve', 'arm protection', '手臂防护']),
        ('防割服（Cut-resistant clothing）', '中',
         ['防护服', 'protective clothing', 'coverall', '工装', '安全服']),
    ]

    def get_product_match(self, industry, products, notes=""):
        text = f"{industry or ''} {products or ''} {notes or ''}".lower()
        if not text.strip():
            return []
        results = []
        for name, priority, keywords in self._PRODUCT_RULES:
            if any(k in text for k in keywords):
                results.append({'product': name, 'priority': priority})
        return results

    # ==============================================================
    # 时区建议
    # ==============================================================

    _TIMEZONE_MAP = {
        'germany': ('UTC+1', 1, '15:30'), 'france': ('UTC+1', 1, '15:30'),
        'italy': ('UTC+1', 1, '15:30'), 'spain': ('UTC+1', 1, '15:30'),
        'uk': ('UTC+0', 0, '17:30'), 'netherlands': ('UTC+1', 1, '15:30'),
        'belgium': ('UTC+1', 1, '15:30'), 'sweden': ('UTC+1', 1, '15:30'),
        'norway': ('UTC+1', 1, '15:30'), 'finland': ('UTC+2', 2, '14:30'),
        'denmark': ('UTC+1', 1, '15:30'), 'poland': ('UTC+1', 1, '15:30'),
        'czech': ('UTC+1', 1, '15:30'), 'austria': ('UTC+1', 1, '15:30'),
        'switzerland': ('UTC+1', 1, '15:30'), 'usa': ('UTC-5~-8', -5, '22:30'),
        'united states': ('UTC-5~-8', -5, '22:30'), 'canada': ('UTC-5~-8', -5, '22:30'),
        'mexico': ('UTC-6~-8', -6, '23:30'), 'australia': ('UTC+10~+11', 10, '07:30'),
        'japan': ('UTC+9', 9, '08:30'), 'korea': ('UTC+9', 9, '08:30'),
        'india': ('UTC+5:30', 5.5, '12:00'), 'brazil': ('UTC-3', -3, '20:30'),
        'turkey': ('UTC+3', 3, '14:30'), 'russia': ('UTC+3~+12', 3, '14:30'),
    }

    def get_timezone_advice(self, country):
        if not country:
            return None
        cl = country.lower().strip()
        for key, (tz, offset, cst) in self._TIMEZONE_MAP.items():
            if key in cl or cl in key:
                return {'tz': tz, 'cst_send': cst, 'label': country}
        if any(eu in cl for eu in ['europe', 'europa']):
            return {'tz': 'UTC+1', 'cst_send': '15:30', 'label': country}
        return None

    # ==============================================================
    # SOP 跟进节奏
    # ==============================================================

    @staticmethod
    def _add_working_days(from_date, days):
        current = from_date
        added = 0
        while added < days:
            current += timedelta(days=1)
            if current.weekday() < 5:
                added += 1
        return current

    def calculate_next_follow_up(self, customer_id):
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
                WHERE customer_id = %s
                ORDER BY created_at DESC
            """, conn, params=(customer_id,))
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    # ==============================================================
    # 邮件历史
    # ==============================================================

    def add_email_history(self, customer_id, subject, content):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM email_history WHERE customer_id = %s", (customer_id,))
            max_version = cursor.fetchone()[0] or 0
            version = max_version + 1
            cursor.execute("""
                INSERT INTO email_history (customer_id, version, email_subject, email_content)
                VALUES (%s, %s, %s, %s)
            """, (customer_id, version, subject, content))
            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (%s, %s, %s)
            """, (customer_id, "生成邮件", f"AI开发邮件 v{version} 已保存"))
            cursor.execute("""
                UPDATE customers SET last_follow_up_date = %s WHERE id = %s
            """, (datetime.now().strftime('%Y-%m-%d'), customer_id))
            conn.commit()
            conn.close()
            return version, None
        except Exception as e:
            return None, str(e)

    def record_follow_up(self, customer_id, subject, content):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM email_history WHERE customer_id = %s", (customer_id,))
            max_v = cursor.fetchone()[0] or 0
            version = max_v + 1
            cursor.execute("""
                INSERT INTO email_history (customer_id, version, email_subject, email_content)
                VALUES (%s, %s, %s, %s)
            """, (customer_id, version, subject, content))
            cursor.execute("""
                INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                VALUES (%s, %s, %s)
            """, (customer_id, "跟进邮件", f"跟进邮件 v{version} 已保存"))
            cursor.execute("""
                UPDATE customers SET last_follow_up_date = %s WHERE id = %s
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
                WHERE customer_id = %s
                ORDER BY version DESC
            """, conn, params=(customer_id,))
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    # ==============================================================
    # 邮件模板
    # ==============================================================

    def add_email_template(self, name, category, subject, content):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO email_templates (name, category, subject, content)
                VALUES (%s, %s, %s, %s)
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
            cursor.execute("DELETE FROM email_templates WHERE id = %s", (template_id,))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    # ==============================================================
    # 系统设置
    # ==============================================================

    def get_setting(self, key):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = %s", (key,))
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
                INSERT INTO system_settings (setting_key, setting_value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (setting_key)
                DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = NOW()
            """, (key, value))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    # ==============================================================
    # 知识库
    # ==============================================================

    def add_knowledge(self, category, title, content):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO knowledge_base (category, title, content)
                VALUES (%s, %s, %s)
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

    # ==============================================================
    # 数据备份与恢复
    # ==============================================================

    def backup_data(self, backup_path):
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
                        cursor.execute("""
                            SELECT column_name FROM information_schema.columns
                            WHERE table_name = %s AND table_schema = 'public'
                            ORDER BY ordinal_position
                        """, (sheet_name,))
                        columns = [row['column_name'] for row in cursor.fetchall()]
                        pd.DataFrame(columns=columns).to_excel(writer, sheet_name=sheet_name, index=False)
                    else:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def restore_data(self, backup_path):
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
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = %s AND table_schema = 'public'
                    ORDER BY ordinal_position
                """, (table_name,))
                return [row['column_name'] for row in cursor.fetchall()]

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
                        cursor.execute("""
                            INSERT INTO system_settings (setting_key, setting_value)
                            VALUES (%s, %s)
                            ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value
                        """, (key, value))

            if not templates_df.empty:
                for _, row in templates_df.iterrows():
                    d = row_to_dict(row, tpl_valid)
                    name = d.get('name')
                    if not name:
                        continue
                    cursor.execute("""
                        INSERT INTO email_templates (name, category, subject, content)
                        VALUES (%s, %s, %s, %s)
                    """, (name, d.get('category'), d.get('subject'), d.get('content')))

            restored_count = 0
            for _, row in customers_df.iterrows():
                d = row_to_dict(row, cust_valid)
                if not str(d.get('company_name', '') or '').strip():
                    continue
                fields = [f for f in cust_valid if f in d]
                values = [d[f] for f in fields]
                placeholders = ', '.join(['%s' for _ in fields])
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
                    cursor.execute("""
                        INSERT INTO follow_up_timeline (customer_id, event_type, event_content)
                        VALUES (%s, %s, %s)
                    """, (cid, etype, d.get('event_content')))

            if not email_history_df.empty:
                for _, row in email_history_df.iterrows():
                    d = row_to_dict(row, email_valid)
                    cid = d.get('customer_id')
                    if cid is None:
                        continue
                    cursor.execute("""
                        INSERT INTO email_history (customer_id, version, email_subject, email_content)
                        VALUES (%s, %s, %s, %s)
                    """, (cid, d.get('version', 1), d.get('email_subject'), d.get('email_content')))

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
