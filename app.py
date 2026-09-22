from io import BytesIO
import sqlite3
import pandas as pd
import streamlit as st

# إعدادات الصفحة
st.set_page_config(
    page_title="نظام إدارة المحفظة المالية الكبرى - ASIA PAY", layout="wide"
)

# --- لوحة التحكم في الأعلى ---
st.markdown(
    "<h2 style='text-align: center; color: #1E3A8A;'>💰 نظام إدارة المحفظة"
    " المالية - ASIA PAY</h2>",
    unsafe_allow_html=True,
)

# استخدام الـ Tabs الخمسة
tab1, tab2, tab3, tab_kpi, tab_wr = st.tabs([
    "💳 محفظة ASIA PAY",
    "📊 المقارنة بين شهرين",
    "⭐ نسبة الإنجاز",
    "📈 KPI",
    "📑 رصيد Organizing E-money",
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


# الحفاظ على الحالة
if "combined_df" not in st.session_state:
  st.session_state["combined_df"] = None

# ====================================================
# القسم الأول: محفظة ASIA PAY
# ====================================================
with tab1:
  st.markdown("### 💼 محفظة ASIA PAY (قاعدة بيانات دائمة)")
  st.markdown("---")
  df = load_wallet_from_db()
  last_balance = get_latest_balance()
  total_deposit = (
      df[df["نوع العملية"] == "إيداع للمحفظة"]["المبلغ"].sum()
      if not df.empty and "نوع العملية" in df.columns
      else 0.0
  )

  col1, col2, col3 = st.columns(3)
  with col1:
    st.metric(
        label="الرصيد الفعلي الحالي في المحفظة", value=f"{last_balance:,.2f} د.ع"
    )
  with col2:
    st.metric(
        label="إجمالي مبالغ الإيداعات فقط", value=f"{total_deposit:,.2f} د.ع"
    )
  with col3:
    st.metric(
        label="إجمالي عدد الحركات المسجلة",
        value=str(len(df)) if not df.empty else "0",
    )

  st.markdown("---")
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
          placeholder="اكتب المبلغ هنا...",
      )
      deposit_reason = st.text_input("سبب الإيداع / اسم المودع")
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
          st.success("تم حفظ الإيداع بنجاح!")
          st.rerun()

  with c2:
    st.subheader("📤 سحب كاش / مديونية")
    with st.form("withdraw_form", clear_on_submit=True):
      withdraw_amount = st.number_input(
          "المبلغ",
          value=None,
          min_value=0.0,
          step=1000.0,
          format="%.2f",
          placeholder="اكتب المبلغ هنا...",
      )
      withdraw_reason = st.text_input("اسم المكاتب / المسؤول")
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
          st.success("تم حفظ السحب بنجاح!")
          st.rerun()

  with c3:
    st.subheader("🔄 استرجاع للمحفظة")
    with st.form("return_form", clear_on_submit=True):
      return_amount = st.number_input(
          "المبلغ الراجع",
          value=None,
          min_value=0.0,
          step=1000.0,
          format="%.2f",
          placeholder="اكتب المبلغ هنا...",
      )
      return_reason = st.text_input("سبب الاسترجاع")
      submit_return = st.form_submit_button("إلغاء واسترجاع")
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
          st.success("تم الاسترجاع بنجاح!")
          st.rerun()

  st.markdown("---")
  st.subheader("📋 السجل التفصيلي للعمليات")
  if not df.empty:
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True)


# ====================================================
# القسم الثاني والثالث والرابع: (كما هي أو اختصاراً)
# ====================================================
with tab2:
  st.markdown("### 📊 المقارنة بين شهرين")
with tab3:
  st.markdown("### ⭐ نسبة الإنجاز والتقييم")
with tab_kpi:
  st.markdown("### 📈 لوحة مؤشرات الأداء (KPI)")


# ====================================================
# التبويب الخامس: استخراج رصيد Organizing E-money من شيت Wallet Report
# ====================================================
with tab_wr:
  st.markdown(
      "### 📑 تقرير أرصدة Short Code لـ (Organizing E-money) من شيت Wallet"
      " Report"
  )
  wr_file = st.file_uploader(
      "اختر ملف الإكسل (يحتوي على شيت Wallet Report)",
      type=["xlsx", "xls"],
      key="wr_excel_file",
  )
  wr_sheet_name = st.text_input(
      "اسم الشيت (افتراضي: Wallet Report)", value="Wallet Report"
  )

  if wr_file is not None:
    try:
      df_wr = pd.read_excel(wr_file, sheet_name=wr_sheet_name)
      st.write("أعمدة الشيت المكتشفة:", list(df_wr.columns))
      df_wr.columns = df_wr.columns.astype(str).str.strip()

      # اختيار الأعمدة أوتوماتيك أو باليد للمساعدة
      default_sc = (
          "Short Code"
          if "Short Code" in df_wr.columns
          else (df_wr.columns[0] if len(df_wr.columns) > 0 else "")
      )
      default_h = (
          "H"
          if "H" in df_wr.columns
          else (df_wr.columns[7] if len(df_wr.columns) > 7 else "")
      )
      default_bal = (
          "Balance"
          if "Balance" in df_wr.columns
          else (df_wr.columns if len(df_wr.columns) > 1 else "")
      )

      col_a, col_b, col_c = st.columns(3)
      sc_col = col_a.text_input("اسم عمود Short Code:", value=str(default_sc))
      h_col = col_b.text_input("اسم عمود H (النوع):", value=str(default_h))
      bal_col = col_c.text_input("اسم عمود Balance (الرصيد):", value=str(default_bal))

      if sc_col in df_wr.columns and bal_col in df_wr.columns:
        # تصفية عمود H على "organizing e-money" (أو مطابقة مرنة)
        if h_col in df_wr.columns:
          mask_h = (
              df_wr[h_col]
              .astype(str)
              .str.strip()
              .str.lower()
              .str.contains("organizing e-money", case=False, na=False)
          )
          filtered_df = df_wr[mask_h].copy()
        else:
          # لو عمود H مو معروف تماماً، نبحث بداخل كل الصفوف
          mask_general = df_wr.apply(
              lambda r: r.astype(str)
              .str.contains("organizing e-money", case=False, na=False)
              .any(),
              axis=1,
          )
          filtered_df = df_wr[mask_general].copy()

        # تنظيف عمود Balance وتحويله إلى رقم حقيقي (numeric)
        raw_bal_series = filtered_df[bal_col].astype(str)
        cleaned_bal = (
            raw_bal_series.str.replace(",", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace("IQD", "", regex=False)
            .str.replace("د.ع", "", regex=False)
        )
        filtered_df["Numeric_Balance"] = pd.to_numeric(
            cleaned_bal, errors="coerce"
        ).fillna(0.0)
        filtered_df["Clean_Short_Code"] = (
            filtered_df[sc_col].astype(str).str.strip()
        )

        # تجميع الرصيد لكل Short Code
        grouped_result = (
            filtered_df.groupby("Clean_Short_Code")["Numeric_Balance"]
            .sum()
            .reset_index()
        )
        grouped_result.rename(
            columns={
                "Clean_Short_Code": "Short Code",
                "Numeric_Balance": "Total Numeric Balance",
            },
            inplace=True,
        )

        st.subheader("📊 النتيجة النهائية: كل Short Code والرصيد (رقمي)")
        st.dataframe(grouped_result, use_container_width=True)

        # زر تحميل النتيجة
        out_buf = BytesIO()
        with pd.ExcelWriter(out_buf, engine="openpyxl") as w:
          grouped_result.to_excel(w, index=False)
        out_buf.seek(0)
        st.download_button(
            label="📥 تحميل تقرير أرصدة Organizing E-money (Excel)",
            data=out_buf,
            file_name="Organizing_E_Money_Balances.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
      else:
        st.warning("⚠️ يرجى التأكد أن أسماء الأعمدة المدخلة مطابقة لما في الشيت.")
    except Exception as err:
      st.error(f"⚠️ حدث خطأ أثناء قراءة الشيت: {err}")
  else:
    st.info("📌 الرجاء رفع ملف الإكسل للبدء استخراج الأرصدة.")
