"""无状态工具函数：评分、健康度、联系方式解析、工作日计算等"""

import re
import pandas as pd
from datetime import datetime, timedelta, date


def extract_domain(email_or_website):
    if not email_or_website:
        return None
    if '@' in email_or_website:
        return email_or_website.split('@')[-1].lower()
    if '://' in email_or_website:
        return email_or_website.split('://')[-1].split('/')[0].lower().replace('www.', '')
    return email_or_website.split('/')[0].lower().replace('www.', '')


def calculate_auto_score(customer_data):
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
    eu_countries = ['germany', 'france', 'italy', 'spain', 'uk', 'netherlands',
                    'belgium', 'sweden', 'norway', 'finland', 'denmark',
                    'poland', 'czech', 'austria', 'switzerland']
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


def get_customer_grade_by_score(score):
    if score >= 85:
        return 'A'
    elif score >= 60:
        return 'B'
    else:
        return 'C'


def get_customer_health(last_follow_up_date):
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


def is_dst_season(today=None):
    if today is None:
        today = date.today()
    return 4 <= today.month <= 10


def add_working_days(from_date, days):
    current = from_date
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def parse_contacts(raw_text):
    """从联系方式字段中提取邮箱、电话、联系人姓名，返回 (email, phone, contact_person)"""
    email, phone, person = '', '', ''
    if not raw_text or not str(raw_text).strip():
        return email, phone, person
    text = str(raw_text).strip()

    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if email_match:
        email = email_match.group(0).strip()

    phone_match = re.search(
        r'(?:(?:Tel|电话|Phone)[.:]*\s*)?(\+?\d{1,4}[\s-]?\d{2,5}[\s-]?\d{3,5}[\s-]?\d{2,4}(?:[\s-]?\d{2,5})?)',
        text
    )
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
