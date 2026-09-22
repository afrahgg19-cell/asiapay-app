from io import BytesIO
import os
import sqlite3
import pandas as pd
import streamlit as st

# إعدادات الصفحة
st.set_page_config(
    page_title="نظام إدارة المحفظة المالية الكبرى - ASIA PAY",
    layout="wide"
)

# --- لوحة التحكم في الأعلى ---
st.markdown(
    "<h2 style='text-align: center; color: #1E3A8A;'>💰 نظام إدارة المحفظة"
    " المالية - ASIA PAY</h2>",
    unsafe_allow_html=True,
)

# استخدام الـ Tabs الأربعة العلوية
tab1, tab2, tab3, tab_kpi = st.tabs([
    "💳 محفظة ASIA PAY",
    "📊 المقارنة بين شهرين",
    "⭐ نسبة الإنجاز",
    "📈 KPI",
])

# --- قاعدة بيانات SQLite للمحفظة ---
DB_FILE = "asia_pay_wallet.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS wallet_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            op_type TEXT,
            amount REAL,
            details TEXT,
            payment_method TEXT,
            debt_status TEXT,
            remaining_balance REAL
        )
    """)
    conn.commit()
    conn.close()


init_db()


def load_wallet_from_db():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM wallet_operations", conn)
    conn.close()

    if not df.empty:
        df = df.rename(
            columns={
                "timestamp": "التاريخ",
                "op_type": "نوع العملية",
                "amount": "المبلغ",
                "details": "التفاصيل / الجهة / السبب",
                "payment_method": "طريقة الدفع",
                "debt_status": "حالة الديون",
                "remaining_balance": "الباقي"
            }
        )
    return df
