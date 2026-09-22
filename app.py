import os
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


# --- الحفاظ على حالة الجرد الكلي ومقارنة الشهور في الذاكرة ---
if "pivot_result" not in st.session_state:
  st.session_state["pivot_result"] = None
if "combined_df" not in st.session_state:
  st.session_state["combined_df"] = None
if "perf_summary" not in st.session_state:
  st.session_state["perf_summary"] = None


# ====================================================
# القسم الأول: محفظة ASIA PAY (محمي بـ SQLite)
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
          value=0.0,
          min_value=0.0,
          step=1000.0,
          format="%.2f",
          key="dep_amt",
      )
      deposit_reason = st.text_input("سبب الإيداع / اسم المودع", key="dep_res")
      submit_deposit = st.form_submit_button("حفظ الإيداع")
      if submit_deposit:
        if deposit_amount > 0:
          current_bal = get_latest_balance()
          new_bal = current_bal + deposit_amount
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
                  deposit_amount,
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
          value=0.0,
          min_value=0.0,
          step=1000.0,
          format="%.2f",
          key="wit_amt",
      )
      withdraw_reason = st.text_input(
          "اسم المكاتب / السحب منه / المسؤول", key="wit_res"
      )
      payment_method = st.selectbox(
          "طريقة الدفع / الحالة", ["كاش", "ماستر كارد", "مديونية (دين)"]
      )
      submit_withdraw = st.form_submit_button("حفظ السحب")
      if submit_withdraw:
        if withdraw_amount > 0:
          current_bal = get_latest_balance()
          new_bal = current_bal - withdraw_amount
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
                  withdraw_amount,
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
          value=0.0,
          min_value=0.0,
          step=1000.0,
          format="%.2f",
          key="ret_amt",
      )
      return_reason = st.text_input("سبب الاسترجاع / من الجهة", key="ret_res")
      submit_return = st.form_submit_button("إلغاء واسترجاع للمحفظة")
      if submit_return:
        if return_amount > 0:
          current_bal = get_latest_balance()
          new_bal = current_bal + return_amount
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
                  return_amount,
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
          else combined_df.columns
          if len(combined_df.columns) > 2
          else combined_df.columns[0]
      )
      combined_df["Arabic Translation"] = combined_df[reason_col].apply(
          lambda x: translation_dict.get(str(x), str(x))
      )

      code_col = (
          "Short Code"
          if "Short Code" in combined_df.columns
          else combined_df.columns[0]
      )
      name_col = (
          "Arabic Name"
          if "Arabic Name" in combined_df.columns
          else (
              combined_df.columns
              if len(combined_df.columns) > 1
              else combined_df.columns[0]
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

      st.session_state["pivot_result"] = pivot_result
      st.session_state["combined_df"] = combined_df

      st.success("✅ تمت معالجة وحفظ المقارنة بين الشهرين بنجاح!")

    except Exception as e:
      st.error(f"⚠️ حدث خطأ أثناء المعالجة: {e}")

  if st.session_state["pivot_result"] is not None:
    st.subheader("📋 جدول مقارنة الجرد المحفوظ")
    st.dataframe(st.session_state["pivot_result"], use_container_width=True)

    output_filename = "Final_Inventory_Comparison_Report.xlsx"
    st.session_state["pivot_result"].to_excel(output_filename, index=False)
    with open(output_filename, "rb") as f:
      st.download_button(
          label="📥 تحميل تقرير المقارنة (Excel)",
          data=f,
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
    df_combined = st.session_state["combined_df"]

    code_col = (
        "Short Code"
        if "Short Code" in df_combined.columns
        else df_combined.columns[0]
    )
    name_col = (
        "Arabic Name"
        if "Arabic Name" in df_combined.columns
        else (
            df_combined.columns
            if len(df_combined.columns) > 1
            else df_combined.columns[0]
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

      st.session_state["perf_summary"] = perf_summary
      st.success("✅ تم احتساب نسبة الإنجاز والتقييم للمكاتب!")
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
# التبويب الرابع: KPI (عمود H للكود، F للاسم، أعداد العمليات من C، و B2B تحويل من T إلى أرقام)
# ====================================================
with tab_kpi:
  st.markdown("### 📈 لوحة مؤشرات الأداء (KPI)")
  st.write(
      "تجميع Short Code (عمود H)، الاسم بالعربي (عمود F)، عد العمليات"
      " من عمود C، واستخراج وتحويل مبالغ business to business transfer من عمود T إلى أرقام."
  )

  kpi_uploaded_file = st.file_uploader(
      "اختر ملف الإكسل الخاص بـ KPI",
      type=["xlsx", "xls"],
      key="kpi_tab_uploader",
  )

  if kpi_uploaded_file is not None:
    try:
      kpi_df = pd.read_excel(kpi_uploaded_file)
      cols_list = kpi_df.columns.tolist()

      # تحديد المواقع آمنًا (A=0, B=1, C=2, F=5, H=7, T=19)
      h_idx = 7 if len(cols_list) > 7 else 0
      f_idx = 5 if len(cols_list) > 5 else 0
      c_idx = 2 if len(cols_list) > 2 else 0
      t_idx = 19 if len(cols_list) > 19 else (len(cols_list) - 1)

      work_kpi = pd.DataFrame()
      work_kpi["H_clean"] = (
          kpi_df["H"].astype(str).str.strip()
          if "H" in kpi_df.columns
          else kpi_df.iloc[:, h_idx].astype(str).str.strip()
      )
      work_kpi["F_clean"] = (
          kpi_df["Arabic Name"].astype(str).str.strip()
          if "Arabic Name" in kpi_df.columns
          else (
              kpi_df["F"].astype(str).str.strip()
              if "F" in kpi_df.columns
              else kpi_df.iloc[:, f_idx].astype(str).str.strip()
          )
      )
      work_kpi["C_clean"] = (
          kpi_df["C"].astype(str).str.strip()
          if "C" in kpi_df.columns
          else kpi_df.iloc[:, c_idx].astype(str).str.strip()
      )

      # استخراج عمود T كنص ومعالجة القيم النصية
      raw_t_series = (
          kpi_df["T"].astype(str)
          if "T" in kpi_df.columns
          else kpi_df.iloc[:, t_idx].astype(str)
      )
      work_kpi["T_text"] = raw_t_series.str.strip()

      # تحويل النصوص في عمود T إلى قيم رقمية بدقة (مع التعامل مع الفواصل الآلاف)
      cleaned_t_numeric = (
          work_kpi["T_text"]
          .str.replace(",", "", regex=False)
          .str.replace(" ", "", regex=False)
      )
      work_kpi["T_num"] = pd.to_numeric(
          cleaned_t_numeric, errors="coerce"
      ).fillna(0.0)

      kpi_rows_list = []
      for (h_v, f_v), grp in work_kpi.groupby(
          ["H_clean", "F_clean"], dropna=False
      ):
        row_item = {
            "Short Code (H)": h_v,
            "Arabic Name (F)": f_v,
        }

        # عدد العمليات لكل نوع من عمود C
        c_value_counts = grp["C_clean"].value_counts()
        for op_name, op_count in c_value_counts.items():
          col_key = f"عدد ({op_name})"
          if col_key not in row_item:
            row_item[col_key] = 0
          row_item[col_key] += op_count

        # فلترة عمليات business to business transfer (مطابقة غير حساسة لحالة الأحرف)
        b2b_mask = (
            grp["C_clean"]
            .str.lower()
            .str.contains("business to business transfer", na=False)
        )

        # جمع الأرقام المحولة من عمود T لهذه الصفوف
        b2b_total_num = grp.loc[b2b_mask, "T_num"].sum()

        # الاحتفاظ بالنصوص الأصلية للمقارنة أو العرض
        b2b_texts = [
            t
            for t in grp.loc[b2b_mask, "T_text"].tolist()
            if str(t).lower() not in ["nan", "none", "", "nat"]
        ]

        row_item["مجموع مبالغ B2B (رقمي محول من T)"] = b2b_total_num
        row_item["نصوص B2B الأصلية (T)"] = (
            " | ".join(b2b_texts) if b2b_texts else "لا يوجد"
        )

        kpi_rows_list.append(row_item)

      final_kpi_table = pd.DataFrame(kpi_rows_list).fillna(0)
      st.subheader("📋 نتيجة تقرير الـ KPI")
      st.dataframe(final_kpi_table, use_container_width=True)

      out_kpi_name = "KPI_Report_Summary.xlsx"
      final_kpi_table.to_excel(out_kpi_name, index=False)
      with open(out_kpi_name, "rb") as f_down:
        st.download_button(
            label="📥 تحميل تقرير KPI نهائي (Excel)",
            data=f_down,
            file_name=out_kpi_name,
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            key="download_kpi_excel",
        )

    except Exception as err:
      st.error(f"⚠️ خطأ أثناء معالجة ملف الـ KPI: {err}")
  else:
    st.info("📌 يرجى رفع ملف الإكسل الخاص بالـ KPI لعرض التجميعات المطلوبة.")
