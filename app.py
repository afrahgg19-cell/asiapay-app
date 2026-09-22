from io import BytesIO
import os
import re
import sqlite3
import pandas as pd
import streamlit as st

# ====================================================
# إعدادات الصفحة
# ====================================================
st.set_page_config(
    page_title="نظام إدارة المحفظة المالية الكبرى - ASIA PAY", layout="wide"
)

st.markdown(
    "<h2 style='text-align: center; color: #1E3A8A;'>💰 نظام إدارة المحفظة"
    " المالية - ASIA PAY</h2>",
    unsafe_allow_html=True,
)

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


# ====================================================
# دوال مساعدة عامة
# ====================================================
def clean_office_code_column(df_target):
  if df_target is None or df_target.empty:
    return df_target
  df_clean = df_target.copy()
  for col in df_clean.columns:
    col_str_lower = str(col).lower()
    if (
        "تل" in str(col)
        or "short code" in col_str_lower
        or "g_clean" in col_str_lower
        or "code" in col_str_lower
    ):
      df_clean[col] = (
          df_clean[col]
          .astype(str)
          .str.replace(r"\.0$", "", regex=True)
          .replace({"nan": "", "NaN": "", "None": ""})
      )
  return df_clean


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
  return clean_office_code_column(df)


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


def get_col_safe(preferred_name, fallback_idx, df_target):
  if preferred_name in df_target.columns:
    return preferred_name
  cols_local = [str(c).strip() for c in df_target.columns.tolist()]
  if len(cols_local) > fallback_idx:
    return df_target.columns[fallback_idx]
  return df_target.columns[0] if len(cols_local) > 0 else None


# --- تهيئة الحفظ المؤقت (Session State) ---
if "pivot_result" not in st.session_state:
  st.session_state["pivot_result"] = None
if "combined_df" not in st.session_state:
  st.session_state["combined_df"] = None
if "perf_summary" not in st.session_state:
  st.session_state["perf_summary"] = None

# ====================================================
# استخدام الـ Tabs (4 تبويبات)
# ====================================================
tab1, tab2, tab3, tab_kpi = st.tabs([
    "💳 محفظة ASIA PAY",
    "📊 المقارنة بين شهرين",
    "⭐ نسبة الإنجاز",
    "📈 KPI والأرصدة",
])

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
        label="الرصيد (الفعلي) الحالي في المحفظة", value=f"{last_balance:,.2f} د.ع"
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
          st.success("تم حفظ الإيداع وتحديث الرصيد في قاعدة البيانات بنجاح!")
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
          st.success("تم حفظ السحب وتحديث الرصيد في قاعدة البيانات بنجاح!")
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
  st.subheader("📋 السجل التفصيلي للعمليات")
  if not df.empty:
    display_df = df.drop(columns=["id"], errors="ignore")
    st.dataframe(display_df, use_container_width=True)

    with st.expander("✏️ تعديل أو حذف عملية سابقة من السجل"):
      if "id" in df.columns:
        row_ids = df["id"].tolist()
        selected_id = st.selectbox(
            "اختر رقم السجل (ID) للتعديل أو الحذف:", row_ids
        )
        if selected_id:
          row_data = df[df["id"] == selected_id].iloc[0]
          with st.form("edit_row_form"):
            st.write(
                f"تعديل السجل ID: {selected_id} | التاريخ:"
                f" {row_data['التاريخ']}"
            )
            new_edit_amount = st.number_input(
                "تعديل المبلغ",
                value=float(row_data["المبلغ"]),
                step=1000.0,
                format="%.2f",
            )
            new_edit_reason = st.text_input(
                "تعديل التفاصيل / الجهة / السبب",
                value=str(row_data["التفاصيل / الجهة / السبب"]),
            )

            col_e1, col_e2 = st.columns(2)
            submit_edit = col_e1.form_submit_button("💾 حفظ التعديلات")
            submit_delete = col_e2.form_submit_button(
                "🗑️ حذف هذا السجل نهائياً"
            )

            if submit_edit:
              conn = sqlite3.connect(DB_FILE)
              c = conn.cursor()
              c.execute(
                  """
                                UPDATE wallet_operations 
                                SET amount = ?, details = ? 
                                WHERE id = ?
                            """,
                  (new_edit_amount, new_edit_reason, int(selected_id)),
              )
              conn.commit()
              conn.close()
              st.success("تم تحديث السجل بنجاح!")
              st.rerun()

            if submit_delete:
              conn = sqlite3.connect(DB_FILE)
              c = conn.cursor()
              c.execute(
                  "DELETE FROM wallet_operations WHERE id = ?",
                  (int(selected_id),),
              )
              conn.commit()
              conn.close()
              st.success("تم حذف السجل بنجاح!")
              st.rerun()
  else:
    st.info("لا توجد عمليات مسجلة حتى الآن.")

  st.markdown("---")
  st.subheader("📊 جرد الحسابات والإحصائيات الشاملة")
  if not df.empty:
    total_withdrawn = (
        df[df["نوع العملية"] == "سحب كاش"]["المبلغ"].sum()
        if "نوع العملية" in df.columns
        else 0.0
    )
    total_returned = (
        df[df["نوع العملية"] == "استرجاع للمحفظة"]["المبلغ"].sum()
        if "نوع العملية" in df.columns
        else 0.0
    )
    current_remaining = get_latest_balance()

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
      st.metric("إجمالي السحوبات", f"{total_withdrawn:,.2f} د.ع")
    with col_s2:
      st.metric("إجمالي الإيداعات", f"{total_deposit:,.2f} د.ع")
    with col_s3:
      st.metric("إجمالي المبالغ المسترجعة", f"{total_returned:,.2f} د.ع")
    with col_s4:
      st.metric("صافي رصيد المحفظة النهائي", f"{current_remaining:,.2f} د.ع")

  st.markdown("---")
  st.subheader("📋 قائمة الأشخاص والجهات المديونة (غير المسددة)")
  if "حالة الديون" in df.columns:
    debts_df = df[df["حالة الديون"] == "غير مسدد (مديونية)"]
    if not debts_df.empty:
      st.warning(f"تنبيه: لديك {len(debts_df)} مديونيات غير مسددة حالياً.")
      debt_list = []
      debt_map = {}
      for idx, row in debts_df.iterrows():
        label_text = f"ID ({row['id']}) - الجهة/الشخص: {row['التفاصيل / الجهة / السبب']} - المبلغ: {row['المبلغ']} د.ع"
        debt_list.append(label_text)
        debt_map[label_text] = row["id"]

      selected_debt_label = st.selectbox(
          "اختر المديونية لتسديدها:", debt_list
      )
      if st.button("✅ تم التسديد (تحديث وإزالة من المديونية)"):
        real_id = debt_map[selected_debt_label]
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            """
                    UPDATE wallet_operations 
                    SET debt_status = 'تم التسديد' 
                    WHERE id = ?
                """,
            (int(real_id),),
        )
        conn.commit()
        conn.close()
        st.success("تم تسديد المديونية وتحديث حالتها بنجاح!")
        st.rerun()
    else:
      st.info("ممتاز! لا توجد أي مديونيات معلقة حالياً، جميع الحسابات خالصة 🎉.")

# ====================================================
# القسم الثاني: المقارنة بين شهرين
# ====================================================
with tab2:
  st.markdown("### 📊 المقارنة بين أداء المكاتب بين شهرين")
  st.write("قم برفع ملف الشهر الأول والملف الثاني المقارن أدناه.")

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
          c
          for c in combined_df.columns
          if "amount" in str(c).lower() or "مبلغ" in str(c)
      ]
      amt_col = (
          amt_candidates[0] if amt_candidates else combined_df.columns[0]
      )

      def clean_amount(val):
        if pd.isna(val):
          return 0.0
        val_str = str(val).replace(",", "").strip()
        try:
          return float(val_str)
        except:
          return 0.0

      combined_df["Cleaned_Amount"] = combined_df[amt_col].apply(clean_amount)

      translation_dict = {
          (
              "Agency Commission Roll Up from Independent Store to Head Office"
          ): "ترحيل عمولات الوكالة من المتاجر المستقلة إلى الإدارة الرئيسية",
          "Auto Claw Back": "استرجاع تلقائي للأموال",
          "Commission Payment for Head Office": "دفع العمولات للإدارة الرئيسية",
          "Commission Payment for Independent Stores": (
              "دفع العمولات للمتاجر المستقلة"
          ),
          "Commission Roll Down for Independent Store": (
              "تنزيل العمولات للمتاجر المستقلة"
          ),
          "Customer Buy Goods Fee from Merchant": "أجور شراء بضائع من التاجر",
          "Customer Deposit at Agent": "إيداع نقدي للزبون لدى الوكيل",
          "Customer Withdraw at Agent": "سحب نقدي للزبون لدى الوكيل",
          "Organization Buy Airtime": "شراء رصيد / تعبئة من المؤسسة",
          "Organization Buy Electronic Vouchers": "شراء قسائم إلكترونية من المؤسسة",
          "Organization Deposit of Funds": "إيداع أموال للمؤسسة",
          (
              "Organization Inter Account Transfer - ORG to Agent"
          ): "تحويل بين حساب المؤسسة وحساب الوكيل",
          (
              "Organization Intra Account Transfer - Child to Child"
          ): "تحويل داخلي بين الفروع",
      }

      reason_col = (
          "Reason Type"
          if "Reason Type" in combined_df.columns
          else combined_df.columns[0]
      )
      combined_df["Arabic Translation"] = combined_df[reason_col].apply(
          lambda x: translation_dict.get(str(x), str(x))
      )

      code_col = (
          "Short Code"
          if "Short Code" in combined_df.columns
          else ("G" if "G" in combined_df.columns else combined_df.columns[0])
      )
      name_col = (
          "Arabic Name"
          if "Arabic Name" in combined_df.columns
          else (
              "F"
              if "F" in combined_df.columns
              else (
                  combined_df.columns
                  if len(combined_df.columns) > 1
                  else combined_df.columns[0]
              )
          )
      )

      combined_df["عدد حركات"] = 1

      pivot_result = combined_df.pivot_table(
          index=[code_col, name_col, reason_col, "Arabic Translation"],
          columns="Month",
          values=["Cleaned_Amount", "عدد حركات"],
          aggfunc={"Cleaned_Amount": "sum", "عدد حركات": "sum"},
          fill_value=0,
      ).reset_index()

      st.session_state["pivot_result"] = clean_office_code_column(pivot_result)
      st.session_state["combined_df"] = clean_office_code_column(combined_df)

      st.success("✅ تمت معالجة وحفظ المقارنة بين الشهرين بنجاح!")

    except Exception as e:
      st.error(f"⚠️ حدث خطأ أثناء المعالجة: {e}")

  if st.session_state["pivot_result"] is not None:
    st.subheader("📋 جدول مقارنة الجرد المحفوظ")
    st.dataframe(st.session_state["pivot_result"], use_container_width=True)

    output_filename = "Final_Inventory_Comparison_Report.xlsx"
    buffer_pivot = BytesIO()

    df_to_save_pivot = st.session_state["pivot_result"].copy()
    if isinstance(df_to_save_pivot.columns, pd.MultiIndex):
      df_to_save_pivot.columns = [
          "_".join([str(c) for c in col if c])
          for col in df_to_save_pivot.columns
      ]

    with pd.ExcelWriter(buffer_pivot, engine="openpyxl") as writer:
      df_to_save_pivot.to_excel(writer, index=False)
    buffer_pivot.seek(0)

    st.download_button(
        label="📥 تحميل تقرير المقارنة (Excel)",
        data=buffer_pivot,
        file_name=output_filename,
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
  else:
    st.info("💡 يرجى رفع ملفات الشهرين في الأعلى لعرض وجرد البيانات.")

# ====================================================
# القسم الثالث: نسبة الإنجاز للمقارنة بين شهرين
# ====================================================
with tab3:
  st.markdown("### ⭐ نسبة الإنجاز والتقييم للمقارنة بين شهرين")
  st.write(
      "هذا القسم يعتمد على بيانات المقارنة بين الشهور لتقييم إنجاز المكاتب."
  )

  if (
      st.session_state["combined_df"] is not None
      and not st.session_state["combined_df"].empty
  ):
    df_combined = clean_office_code_column(st.session_state["combined_df"])

    code_col = (
        "Short Code"
        if "Short Code" in df_combined.columns
        else ("G" if "G" in df_combined.columns else df_combined.columns[0])
    )
    name_col = (
        "Arabic Name"
        if "Arabic Name" in df_combined.columns
        else (
            "F"
            if "F" in df_combined.columns
            else (
                df_combined.columns
                if len(df_combined.columns) > 1
                else df_combined.columns[0]
            )
        )
    )

    if code_col in df_combined.columns and name_col in df_combined.columns:
      perf_summary = (
          df_combined.groupby([code_col, name_col])
          .agg(
              إجمالي_العمليات=("Cleaned_Amount", "count"),
              مجموع_المبالغ=("Cleaned_Amount", "sum"),
          )
          .reset_index()
      )

      target_benchmark = 10000000.0

      def calc_performance_and_progress(row):
        amt = row["مجموع_المبالغ"]
        progress_pct = min(100.0, (amt / target_benchmark) * 100.0)

        if amt > 5000000:
          perf_desc = "ممتاز (95%)"
          points = int(amt / 10000)
        elif amt > 2000000:
          perf_desc = "جيد جداً (85%)"
          points = int(amt / 10000)
        elif amt > 500000:
          perf_desc = "جيد (75%)"
          points = int(amt / 10000)
        else:
          perf_desc = "مقبول (60%)"
          points = int(amt / 10000)
        return pd.Series([perf_desc, progress_pct, points])

      perf_summary[[
          "نسبة الأداء",
          "نسبة الإنجاز (%)",
          "النقاط المكتسبة",
      ]] = perf_summary.apply(calc_performance_and_progress, axis=1)

      st.session_state["perf_summary"] = clean_office_code_column(perf_summary)
      st.success("✅ تمت محاسبة نسبة الإنجاز والتقييم للمكاتب!")
      st.dataframe(perf_summary, use_container_width=True)

      st.markdown("### 📈 مقارنة نسب الإنجاز للمكاتب")
      chart_df = perf_summary.set_index(name_col)["نسبة الإنجاز (%)"]
      st.bar_chart(chart_df)
    else:
      st.warning("⚠️ الأعمدة المطلوبة غير مطابقة.")
  else:
    st.info(
        "📌 يرجى رفع ملفات الشهرين في تبويب **(📊 المقارنة بين شهرين)** أولاً."
    )

# ====================================================
# التبويب الرابع: KPI + دمج عمود رصيد المحفظة (كرقم دقيق من عمود balance)
# ====================================================
with tab_kpi:
  st.markdown("### 📈 لوحة مؤشرات الأداء (KPI) + رصيد المحفظة (قراءة رقمية)")
  st.write(
      "ارفع **ملف الإكسل** سيتم تنظيف وتصحيح قراءة عمود balance رقمياً بكل"
      " دقة."
  )

  single_excel_file = st.file_uploader(
      "اختر ملف الإكسل (يحتوي Transaction Report / Wallet Report أو جداول"
      " المطابقة)",
      type=["xlsx", "xls"],
      key="single_combined_excel_file_v4",
  )

  if single_excel_file is not None:
    try:
      excel_reader = pd.ExcelFile(single_excel_file)
      sheet_names = excel_reader.sheet_names

      st.write("الأوراق المتاحة في الملف المرفق:", sheet_names)

      trans_sheet_name = (
          next((s for s in sheet_names if "trans" in s.lower() or "حرك" in s), None)
          or sheet_names[0]
      )
      wallet_sheet_name = next(
          (
              s
              for s in sheet_names
              if "wallet" in s.lower() or "محفظ" in s or "report" in s.lower()
          ),
          sheet_names[0],
      )

      kpi_df = pd.read_excel(single_excel_file, sheet_name=trans_sheet_name)
      wallet_source_df = pd.read_excel(
          single_excel_file,
          sheet_name=(
              wallet_sheet_name
              if wallet_sheet_name != trans_sheet_name
              else trans_sheet_name
          ),
      )

      g_col_name = get_col_safe("Short Code", 6, kpi_df)
      f_col_name = get_col_safe("Arabic Name", 5, kpi_df)
      b_col_name = get_col_safe("B", 1, kpi_df)
      t_col_name = get_col_safe("T", 19, kpi_df)

      work_kpi = pd.DataFrame()
      raw_g_series = (
          kpi_df[g_col_name].astype(str).str.strip()
          if g_col_name in kpi_df.columns
          else pd.Series([""] * len(kpi_df))
      )
      work_kpi["G_clean"] = raw_g_series.str.replace(r"\.0$", "", regex=True)

      work_kpi["F_clean"] = (
          kpi_df[f_col_name].astype(str).str.strip()
          if f_col_name in kpi_df.columns
          else pd.Series([""] * len(kpi_df))
      )
      work_kpi["B_clean"] = (
          kpi_df[b_col_name].astype(str).str.strip()
          if b_col_name in kpi_df.columns
          else pd.Series([""] * len(kpi_df))
      )

      raw_t_series = (
          kpi_df[t_col_name].astype(str)
          if t_col_name in kpi_df.columns
          else pd.Series(["0"] * len(kpi_df))
      )
      cleaned_t_numeric = (
          raw_t_series.str.replace(",", "", regex=False)
          .str.replace(" ", "", regex=False)
          .str.replace("$", "", regex=False)
      )
      work_kpi["T_num"] = pd.to_numeric(
          cleaned_t_numeric, errors="coerce"
      ).fillna(0.0)

      # --- بناء قاموس مطابقة Short Code مع Balance بشكل قاطع ومخصص للنصوص المخزنة أرقاماً ---
      opt_lookup = {}
      opt_code_col = None
      for c in wallet_source_df.columns:
        c_low = str(c).lower()
        if "short" in c_low and "code" in c_low:
          opt_code_col = c
          break
      if not opt_code_col and len(wallet_source_df.columns) > 0:
        opt_code_col = wallet_source_df.columns[0]

      balance_col_target = None
      for c in wallet_source_df.columns:
        if str(c).strip().lower() == "balance":
          balance_col_target = c
          break
      if not balance_col_target:
        for c in wallet_source_df.columns:
          if "balance" in str(c).lower():
            balance_col_target = c
            break

      def strict_clean_balance(val):
        if pd.isna(val):
          return 0.0
        val_s = str(val).strip()
        cleaned = re.sub(r"[^\d.-]", "", val_s)
        try:
          return float(cleaned) if cleaned else 0.0
        except:
          return 0.0

      for _, rrow in wallet_source_df.iterrows():
        c_key = (
            str(rrow[opt_code_col]).strip().replace(".0", "")
            if opt_code_col in rrow and pd.notna(rrow[opt_code_col])
            else ""
        )
        if c_key:
          bal_val = (
              strict_clean_balance(rrow[balance_col_target])
              if balance_col_target and balance_col_target in rrow
              else 0.0
          )
          opt_lookup[c_key] = bal_val

      st.success("✅ تمت قراءة المطابقة وتنظيف عمود الأرصدة كأرقام بنجاح.")

      target_ops = [
          "Merchant Payment",
          "Airtime Top-up",
          "Cash In",
          "Cash Out",
          "Bulk B2B Transfer",
          "Super Transaction",
          "E-money Deposit",
          "Electronic Vouchers",
      ]

      kpi_rows_list = []
      for (g_v, f_v), grp in work_kpi.groupby(
          ["G_clean", "F_clean"], dropna=False
      ):
        g_clean_str = str(g_v).strip().replace(".0", "")
        raw_bal_num = opt_lookup.get(g_clean_str, 0.0)

        row_item = {
            "Short Code (G)": g_clean_str,
            "Arabic Name (F)": f_v,
            "رصيد المحفظة": raw_bal_num,
        }

        for op in target_ops:
          count_val = grp["B_clean"].str.lower() == op.lower()
          row_item[f"عدد ({op})"] = int(count_val.sum())

        b2b_mask = (
            grp["B_clean"].str.lower() == "business to business transfer"
        )
        total_b2b_sum = grp.loc[b2b_mask, "T_num"].sum()

        formatted_b2b = (
            f"{int(total_b2b_sum):,}"
            if total_b2b_sum == int(total_b2b_sum)
            else f"{total_b2b_sum:,.2f}"
        )
        row_item["مجموع مبالغ Business to Business Transfer"] = formatted_b2b

        row_item["حركه ال100 الف"] = (
            "Done" if total_b2b_sum > 99000 else ""
        )
        row_item["حركه ال3 مليون"] = (
            "Done" if total_b2b_sum > 2999000 else ""
        )

        high_t_count = int((grp["T_num"] > 4999).sum())
        row_item["عدد الحركات > 4999 (4+)"] = (
            "Done" if high_t_count >= 4 else ""
        )

        kpi_rows_list.append(row_item)

      final_kpi_table = pd.DataFrame(kpi_rows_list)
      final_kpi_table = clean_office_code_column(final_kpi_table)

      st.subheader("📋 نتيجة تقرير الـ KPI (مع عمود رصيد المحفظة الرقمي)")
      st.dataframe(final_kpi_table, use_container_width=True)

      out_kpi_name = "KPI_Report_With_Wallet_Balance.xlsx"
      buffer_kpi = BytesIO()

      with pd.ExcelWriter(buffer_kpi, engine="openpyxl") as writer:
        final_kpi_table.to_excel(writer, index=False)
      buffer_kpi.seek(0)

      st.download_button(
          label="📥 تحميل التقرير النهائي مع رصيد المحفظة (Excel)",
          data=buffer_kpi,
          file_name=out_kpi_name,
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
      )

    except Exception as err:
      st.error(f"⚠️ خطأ أثناء معالجة الملف: {err}")
  else:
    st.info(
        "📌 يرجى رفع ملف الإكسل الذي يحتوي على الحركات والمحفظة لعرض النتائج."
    )
