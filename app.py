from io import BytesIO
import os
import sqlite3
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd
import streamlit as st

# إعدادات الصفحة
st.set_page_config(
    page_title="نظام إدارة المحفظة المالية الكبرى - ASIA PAY", layout="wide"
)

# --- دالة تطبيق تنسيق KPL (رمادي/رصاصي، حدود، خط 14) ---


def apply_kpl_styling_to_sheet(ws):
  header_fill = PatternFill(
      start_color='4A4A4A', end_color='4A4A4A', fill_type='solid'
  )
  header_font = Font(name='Calibri', size=14, bold=True, color='FFFFFF')

  row_fill_white = PatternFill(
      start_color='FFFFFF', end_color='FFFFFF', fill_type='solid'
  )
  row_fill_gray = PatternFill(
      start_color='F5F5F5', end_color='F5F5F5', fill_type='solid'
  )
  cell_font = Font(name='Calibri', size=14, color='000000')

  thin_side = Side(border_style='thin', color='D9D9D9')
  dark_side = Side(border_style='medium', color='595959')
  border_cell = Border(
      left=thin_side, right=thin_side, top=thin_side, bottom=thin_side
  )
  border_header = Border(
      left=thin_side, right=thin_side, top=dark_side, bottom=dark_side
  )

  max_row = ws.max_row
  max_col = ws.max_column

  for row_idx in range(1, max_row + 1):
    is_header = row_idx == 1
    current_row_fill = header_fill if is_header else (
        row_fill_gray if row_idx % 2 == 0 else row_fill_white
    )

    for col_idx in range(1, max_col + 1):
      cell = ws.cell(row=row_idx, column=col_idx)
      cell.fill = current_row_fill
      cell.border = border_header if is_header else border_cell

      if is_header:
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal='center', vertical='center', wrap_text=True
        )
      else:
        cell.font = cell_font
        if isinstance(cell.value, (int, float)):
          cell.alignment = Alignment(horizontal='right', vertical='center')
        else:
          cell.alignment = Alignment(horizontal='left', vertical='center')

  for col in ws.columns:
    max_len = max(len(str(cell.value or '')) for cell in col)
    col_letter = get_column_letter(col[0].column)
    ws.column_dimensions[col_letter].width = max(max_len + 5, 14)

  ws.freeze_panes = 'A2'


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
  c.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_excel_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            office_name TEXT,
            received_amount REAL,
            payment_method TEXT,
            remaining REAL,
            deposited_amount REAL,
            total_deposits REAL,
            returned_amount REAL,
            notes TEXT
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
            "remaining_balance": "الباقي في المحفظة",
        }
    )
  else:
    df = pd.DataFrame(
        columns=[
            "id",
            "التاريخ",
            "نوع العملية",
            "المبلغ",
            "التفاصيل / الجهة / السبب",
            "طريقة الدفع",
            "حالة الديون",
            "الباقي في المحفظة",
        ]
    )
  return df


def get_latest_balance():
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute(
      "SELECT remaining_balance FROM wallet_operations ORDER BY id DESC LIMIT"
      " 1"
  )
  row = c.fetchone()
  conn.close()
  return row[0] if row else 0.0


# الحفاظ على حالة الجرد الكلي في الذاكرة
if "pivot_result" not in st.session_state:
  st.session_state["pivot_result"] = None
if "combined_df" not in st.session_state:
  st.session_state["combined_df"] = None
if "perf_summary" not in st.session_state:
  st.session_state["perf_summary"] = None


# ====================================================
# القسم الأول: محفظة ASIA PAY (مع الربط التلقائي للإكسل)
# ====================================================
with tab1:
  st.markdown("### 💼 محفظة ASIA PAY والربط الذكي لملف الإكسل")
  st.markdown("---")

  # --- رفع ملف الإكسل وربطه بالمؤشرات والديون تلقائياً ---
  st.subheader("📁 رفع ملف الإكسل لربط البيانات وتحديث المؤشرات")
  uploaded_custom_excel = st.file_uploader(
      "اختر ملف الإكسل الخاص بالمكاتب والحسابات لربطه بالنظام",
      type=["xlsx", "xls"],
      key="custom_excel_uploader",
  )

  if uploaded_custom_excel is not None:
    try:
      custom_df = pd.read_excel(uploaded_custom_excel)

      # توحيد قراءة الأعمدة بافتراض أسماء قريبة أو استخدام الأندكسات إن وجدت
      # سنقوم بتنظيف وتخزين البيانات في قاعدة البيانات الدائمة
      conn_ex = sqlite3.connect(DB_FILE)
      custom_df.to_sql(
          "uploaded_excel_data", conn_ex, if_exists="replace", index=False
      )
      conn_ex.close()
      st.success("✅ تم رفع ملف الإكسل وربط البيانات وتحديث لوحة التحكم بنجاح!")
    except Exception as ex_err:
      st.error(f"⚠️ حدث خطأ أثناء قراءة ملف الإكسل المرفوع: {ex_err}")

  # جلب بيانات الإكسل المخزنة للربط
  excel_data_df = pd.DataFrame()
  try:
    conn_ex = sqlite3.connect(DB_FILE)
    excel_data_df = pd.read_sql("SELECT * FROM uploaded_excel_data", conn_ex)
    conn_ex.close()
  except Exception:
    pass

  # حساب المجاميع من ملف الإكسل المرفوع مباشرة لربط المؤشرات العليا
  excel_total_deposits = 0.0
  excel_total_remaining = 0.0
  excel_debts_count = 0

  if not excel_data_df.empty:
    # محاولة البحث عن أعمدة الإيداعات والباقي ديناميكياً
    col_names = [str(c).strip() for c in excel_data_df.columns]

    # البحث عن عمود الإيداعات أو المبالغ المودعة
    dep_col = next(
        (
            c
            for c in col_names
            if any(
                k in c
                for k in [
                    "إيداع",
                    "مودع",
                    "الإيداعات",
                    "deposit",
                    "Deposited",
                    "Total Deposits",
                ]
            )
        ),
        None,
    )
    if not dep_col and len(col_names) > 5:
      dep_col = col_names[5]  # افتراض العمود السادس بناءً على هيكلك

    # البحث عن عمود الباقي أو المديونية
    rem_col = next(
        (
            c
            for c in col_names
            if any(k in c for k in ["الباقي", "باقي", "remaining", "Remaining"])
        ),
        None,
    )
    if not rem_col and len(col_names) > 3:
      rem_col = col_names[3]  # افتراض العمود الرابع

    # تصفية وحساب القيم إذا كانت الأعمدة موجودة وقابلة للتحويل لرقم
    def safe_sum(series):
      if series is None:
        return 0.0
      return pd.to_numeric(
          series.astype(str)
          .str.replace(",", "")
          .str.replace("د.ع", "")
          .str.strip(),
          errors="coerce",
      ).sum()

    if dep_col in excel_data_df.columns:
      excel_total_deposits = safe_sum(excel_data_df[dep_col])

    if rem_col in excel_data_df.columns:
      excel_total_remaining = safe_sum(excel_data_df[rem_col])
      # حساب عدد الجهات التي عليها دين (الباقي أكبر من صفر)
      numeric_rem = pd.to_numeric(
          excel_data_df[rem_col]
          .astype(str)
          .str.replace(",", "")
          .str.strip(),
          errors="coerce",
      )
      excel_debts_count = int((numeric_rem > 0).sum())

  # جلب بيانات العمليات اليدوية من قاعدة البيانات
  df_wallet = load_wallet_from_db()
  manual_balance = get_latest_balance()

  # الدمج الذكي: إذا تم رفع إكسل نأخذ الرصيد والباقي والإيداعات منه، وإلا نأخذ من العمليات اليدوية
  final_display_balance = (
      excel_total_remaining if not excel_data_df.empty else manual_balance
  )
  final_total_deposits = (
      excel_total_deposits
      if not excel_data_df.empty
      else (
          df_wallet[df_wallet["نوع العملية"] == "إيداع للمحفظة"]["المبلغ"].sum()
          if not df_wallet.empty
          else 0.0
      )
  )

  # عرض المؤشرات العلوية المحدثة بالربط
  col1, col2, col3, col_target = st.columns(4)
  with col1:
    st.metric(
        label="الرصيد الفعلي (المتبقي في المحفظة)",
        value=f"{final_display_balance:,.2f} د.ع",
    )
  with col2:
    st.metric(
        label="إجمالي مبالغ الإيداعات (من الإكسل)",
        value=f"{final_total_deposits:,.2f} د.ع",
    )
  with col3:
    st.metric(
        label="إجمالي عدد العمليات / الحركات",
        value=(
            str(len(excel_data_df))
            if not excel_data_df.empty
            else str(len(df_wallet))
        ),
    )
  with col_target:
    deposit_target_val = st.number_input(
        "🎯 تاركت الإيداع (Target)",
        value=st.session_state.get("deposit_target_val", 10000000.0),
        step=500000.0,
        format="%.2f",
        key="deposit_target_input",
    )
    st.session_state["deposit_target_val"] = deposit_target_val
    dep_progress = (
        (final_total_deposits / deposit_target_val) * 100.0
        if deposit_target_val > 0
        else 0.0
    )
    st.metric(
        label="نسبة إنجاز الإيداعات من التاركت", value=f"{dep_progress:,.2f}%"
    )

  st.markdown("---")

  # نماذج الإيداع والسحب اليدوي
  c1, c2, c3 = st.columns(3)
  with c1:
    st.subheader("📥 إيداع للمحفظة")
    with st.form("deposit_form", clear_on_submit=True):
      deposit_amount = st.number_input(
          "المبلغ",
          value=None,
          min_value=0.0,
          step=1000.0,
          format="%.2f",
          key="dep_amt",
          placeholder="اكتب المبلغ هنا...",
      )
      deposit_reason = st.text_input("سبب الإيداع / اسم المودع", key="dep_res")
      submit_deposit = st.form_submit_button("حفظ الإيداع")
      if submit_deposit:
        amt_val = 0.0 if deposit_amount is None else float(deposit_amount)
        if amt_val > 0:
          current_bal = get_latest_balance()
          new_bal = current_bal + amt_val
          conn = sqlite3.connect(DB_FILE)
          c = conn.cursor()
          c.execute(
              """
                        INSERT INTO wallet_operations (timestamp, op_type, amount, details, payment_method, debt_status, remaining_balance)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
              (
                  str(pd.Timestamp.now()),
                  "إيداع للمحفظة",
                  amt_val,
                  deposit_reason,
                  "إيداع",
                  "لا توجد",
                  new_bal,
              ),
          )
          conn.commit()
          conn.close()
          st.success("تم حفظ الإيداع وتحديث الرصيد بنجاح!")
          st.rerun()
        else:
          st.warning("يرجى إدخال مبلغ صحيح أكبر من صفر.")

  with c2:
    st.subheader("📤 سحب كاش / مديونية")
    with st.form("withdraw_form", clear_on_submit=True):
      withdraw_amount = st.number_input(
          "المبلغ",
          value=None,
          min_value=0.0,
          step=1000.0,
          format="%.2f",
          key="wit_amt",
          placeholder="اكتب المبلغ هنا...",
      )
      withdraw_reason = st.text_input(
          "اسم المكاتب / السحب منه / المسؤول", key="wit_res"
      )
      payment_method = st.selectbox(
          "طريقة الدفع / الحالة", ["كاش", "ماستر كارد", "مديونية (دين)"]
      )
      submit_withdraw = st.form_submit_button("حفظ السحب")
      if submit_withdraw:
        amt_val = 0.0 if withdraw_amount is None else float(withdraw_amount)
        if amt_val > 0:
          current_bal = get_latest_balance()
          new_bal = current_bal - amt_val
          debt_status = (
              "غير مسدد (مديونية)"
              if payment_method == "مديونية (دين)"
              else "مكتمل"
          )
          conn = sqlite3.connect(DB_FILE)
          c = conn.cursor()
          c.execute(
              """
                        INSERT INTO wallet_operations (timestamp, op_type, amount, details, payment_method, debt_status, remaining_balance)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
              (
                  str(pd.Timestamp.now()),
                  "سحب كاش",
                  amt_val,
                  withdraw_reason,
                  payment_method,
                  debt_status,
                  new_bal,
              ),
          )
          conn.commit()
          conn.close()
          st.success("تم حفظ السحب وتحديث الرصيد بنجاح!")
          st.rerun()
        else:
          st.warning("يرجى إدخال مبلغ صحيح أكبر من صفر.")

  with c3:
    st.subheader("🔄 استرجاع مبالغ للمحفظة")
    with st.form("return_form", clear_on_submit=True):
      return_amount = st.number_input(
          "المبلغ الراجع",
          value=None,
          min_value=0.0,
          step=1000.0,
          format="%.2f",
          key="ret_amt",
          placeholder="اكتب المبلغ هنا...",
      )
      return_reason = st.text_input("سبب الاسترجاع / من الجهة", key="ret_res")
      submit_return = st.form_submit_button("إلغاء واسترجاع للمحفظة")
      if submit_return:
        amt_val = 0.0 if return_amount is None else float(return_amount)
        if amt_val > 0:
          current_bal = get_latest_balance()
          new_bal = current_bal + amt_val
          conn = sqlite3.connect(DB_FILE)
          c = conn.cursor()
          c.execute(
              """
                        INSERT INTO wallet_operations (timestamp, op_type, amount, details, payment_method, debt_status, remaining_balance)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
              (
                  str(pd.Timestamp.now()),
                  "استرجاع للمحفظة",
                  amt_val,
                  return_reason,
                  "استرجاع",
                  "لا توجد",
                  new_bal,
              ),
          )
          conn.commit()
          conn.close()
          st.success("تم استرجاع المبلغ وإضافته للمحفظة بنجاح!")
          st.rerun()
        else:
          st.warning("يرجى إدخال مبلغ صحيح أكبر من صفر.")

  st.markdown("---")

  # عرض الجدول المرفوع من الإكسل إذا وجد، وإلا عرض العمليات اليدوية
  if not excel_data_df.empty:
    st.subheader("📋 بيانات المكاتب والحسابات المستخرجة من ملف الإكسل المرفوع")
    st.dataframe(excel_data_df, use_container_width=True)
  else:
    st.subheader("📋 السجل التفصيلي للعمليات اليدوية")
    if not df_wallet.empty:
      st.dataframe(df_wallet.drop(columns=["id"], errors="ignore"), use_container_width=True)
    else:
      st.info("لا توجد عمليات مسجلة حتى الآن. قم برفع ملف الإكسل أو إضافة عملية جديدة.")

  st.markdown("---")

  # قسم المديونيات المرتبط بملف الإكسل تلقائياً
  st.subheader("📋 قائمة الأشخاص والجهات المديونة (المستخرجة من الإكسل والحسابات)")
  
  if not excel_data_df.empty and rem_col in excel_data_df.columns:
    # استخراج الصفوف التي تحتوي على مديونية (الباقي > 0)
    numeric_rem_series = pd.to_numeric(
        excel_data_df[rem_col].astype(str).str.replace(",", "").str.strip(),
        errors="coerce",
    ).fillna(0)
    debts_from_excel = excel_data_df[numeric_rem_series > 0]

    if not debts_from_excel.empty:
      st.warning(f"⚠️ تم رصد {len(debts_from_excel)} جهة/شخص عليه مديونية من ملف الإكسل المرفوع:")
      st.dataframe(debts_from_excel, use_container_width=True)
    else:
      st.info("🎉 ممتاز! لا توجد أي مديونيات مسجلة في ملف الإكسل المرفوع.")
  else:
    # الاعتماد على النظام اليدوي للديون إن لم يوجد إكسل
    if "حالة الديون" in df_wallet.columns:
      debts_df = df_wallet[df_wallet["حالة الديون"] == "غير مسدد (مديونية)"]
      if not debts_df.empty:
        st.warning(f"تنبيه: لديك {len(debts_df)} مديونيات يدويّة غير مسددة حالياً.")
        st.dataframe(debts_df, use_container_width=True)
      else:
        st.info("لا توجد مديونيات معلقة.")

# ====================================================
# القسم الثاني: المقارنة بين شهرين
# ====================================================
with tab2:
  st.markdown("### 📊 المقارنة بين أداء المكاتب بين شهرين")
  col_u1, col_u2 = st.columns(2)
  with col_u1:
    uploaded_file_8 = st.file_uploader(
        "اختر ملف الشهر الأول (Excel)", type=["xlsx", "xls"], key="file8"
    )
  with col_u2:
    uploaded_file_9 = st.file_uploader(
        "اختر ملف الشهر الثاني (Excel)", type=["xlsx", "xls"], key="file9"
    )

  if uploaded_file_8 is not None and uploaded_file_9 is not None:
    try:
      df8 = pd.read_excel(uploaded_file_8)
      df9 = pd.read_excel(uploaded_file_9)
      df8["Month"] = "الشهر الأول"
      df9["Month"] = "الشهر الثاني"
      combined_df = pd.concat([df8, df9], ignore_index=True)

      amt_candidates = [
          c for c in combined_df.columns if "amount" in str(c).lower() or "مبلغ" in str(c)
      ]
      amt_col = amt_candidates[0] if amt_candidates else combined_df.columns[0]

      def clean_amount(val):
        if pd.isna(val):
          return 0.0
        try:
          return float(str(val).replace(",", "").strip())
        except:
          return 0.0

      combined_df["Cleaned_Amount"] = combined_df[amt_col].apply(clean_amount)
      combined_df["عدد حركات"] = 1

      code_col = (
          "Short Code"
          if "Short Code" in combined_df.columns
          else combined_df.columns[0]
      )
      name_col = (
          "Arabic Name"
          if "Arabic Name" in combined_df.columns
          else combined_df.columns[1] if len(combined_df.columns) > 1 else combined_df.columns[0]
      )
      reason_col = (
          "Reason Type"
          if "Reason Type" in combined_df.columns
          else combined_df.columns[0]
      )

      pivot_result = combined_df.pivot_table(
          index=[code_col, name_col, reason_col],
          columns="Month",
          values=["Cleaned_Amount", "عدد حركات"],
          aggfunc={"Cleaned_Amount": "sum", "عدد حركات": "sum"},
          fill_value=0,
      ).reset_index()

      st.session_state["pivot_result"] = pivot_result
      st.session_state["combined_df"] = combined_df
      st.success("✅ تمت معالجة وحفظ المقارنة بين الشهرين بنجاح!")
    except Exception as e:
      st.error(f"⚠️ حدث خطأ أثناء المعالجة: {e}")

  if st.session_state["pivot_result"] is not None:
    st.dataframe(st.session_state["pivot_result"], use_container_width=True)

# ====================================================
# القسم الثالث: نسبة الإنجاز
# ====================================================
with tab3:
  st.markdown("### ⭐ نسبة الإنجاز والتقييم للمقارنة بين شهرين")
  if st.session_state["combined_df"] is not None:
    df_combined = st.session_state["combined_df"]
    name_col = (
        "Arabic Name"
        if "Arabic Name" in df_combined.columns
        else df_combined.columns[0]
    )
    perf_summary = (
        df_combined.groupby(name_col)
        .agg(مجموع_المبالغ=("Cleaned_Amount", "sum"))
        .reset_index()
    )
    target_benchmark = 10000000.0
    perf_summary["نسبة الإنجاز (%)"] = (
        perf_summary["مجموع_المبالغ"] / target_benchmark
    ) * 100.0
    st.dataframe(perf_summary, use_container_width=True)
  else:
    st.info("📌 يرجى رفع ملفات الشهرين في تبويب المقارنة أولاً.")

# ====================================================
# التبويب الرابع: KPI
# ====================================================
with tab_kpi:
  st.markdown("### 📈 لوحة مؤشرات الأداء (KPI)")
  kpi_uploaded_file = st.file_uploader(
      "اختر ملف الإكسل الخاص بالحركات و Wallet report (KPI)",
      type=["xlsx", "xls"],
      key="kpi_main_file_final",
  )
  if kpi_uploaded_file is not None:
    try:
      kpi_df = pd.read_excel(kpi_uploaded_file)
      st.dataframe(kpi_df, use_container_width=True)
    except Exception as err:
      st.error(f"⚠️ خطأ: {err}")
  else:
    st.info("📌 يرجى رفع ملف الإكسل الرئيسي للـ KPI.")
