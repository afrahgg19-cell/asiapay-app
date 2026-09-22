from io import BytesIO
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


# تنظيف الشورت كود لإزالة .0 أو المسافات
def clean_code(val):
  if pd.isna(val):
    return ""
  s = str(val).strip()
  if s.endswith(".0"):
    s = s[:-2]
  return s


if "pivot_result" not in st.session_state:
  st.session_state["pivot_result"] = None
if "combined_df" not in st.session_state:
  st.session_state["combined_df"] = None
if "perf_summary" not in st.session_state:
  st.session_state["perf_summary"] = None

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
      st.session_state["combined_df"] = combined_df
      st.success("✅ تم تحميل ومعالجة ملفات المقارنة بنجاح!")
    except Exception as e:
      st.error(f"⚠️ خطأ: {e}")

# ====================================================
# القسم الثالث: نسبة الإنجاز
# ====================================================
with tab3:
  st.markdown("### ⭐ نسبة الإنجاز والتقييم للمقارنة بين شهرين")
  st.info("قسم الإنجاز مرتبط ببيانات المقارنة.")

# ====================================================
# التبويب الرابع: KPI
# ====================================================
with tab_kpi:
  st.markdown("### 📈 لوحة مؤشرات الأداء (KPI)")
  st.write(
      "ارفع **ملف الإكسل الرئيسي** (الشيت الأول للحركات + الشيت الثاني"
      " `Transaction Report` أو `wallet report`)."
  )

  col_k1, col_k2 = st.columns(2)
  with col_k1:
    kpi_uploaded_file = st.file_uploader(
        "ملف الإكسل الرئيسي", type=["xlsx", "xls"], key="kpi_main_single_v9"
    )
  with col_k2:
    rep_uploaded_file = st.file_uploader(
        "ملف المندوبين (اختياري)",
        type=["xlsx", "xls"],
        key="kpi_rep_single_v9",
    )

  if kpi_uploaded_file is not None:
    try:
      excel_file_obj = pd.ExcelFile(kpi_uploaded_file)
      sheet_names = excel_file_obj.sheet_names
      kpi_df = pd.read_excel(excel_file_obj, sheet_name=sheet_names[0])

      # البحث عن شيت wallet report / transaction report
      wallet_report_sheet_name = None
      for s_name in sheet_names:
        l_name = str(s_name).lower()
        if (
            "wallet" in l_name
            or "report" in l_name
            or "transaction" in l_name
        ):
          wallet_report_sheet_name = s_name
          break
      if not wallet_report_sheet_name and len(sheet_names) > 1:
        wallet_report_sheet_name = sheet_names

      g_col_name = (
          "Short Code"
          if "Short Code" in kpi_df.columns
          else (
              kpi_df.columns[6]
              if len(kpi_df.columns) > 6
              else kpi_df.columns[0]
          )
      )
      f_col_name = (
          "Arabic Name"
          if "Arabic Name" in kpi_df.columns
          else (
              kpi_df.columns[5]
              if len(kpi_df.columns) > 5
              else kpi_df.columns[0]
          )
      )
      b_col_name = (
          "B"
          if "B" in kpi_df.columns
          else (kpi_df.columns if len(kpi_df.columns) > 1 else kpi_df.columns[0])
      )
      t_col_name = (
          "T"
          if "T" in kpi_df.columns
          else (
              kpi_df.columns[19]
              if len(kpi_df.columns) > 19
              else kpi_df.columns[0]
          )
      )

      work_kpi = pd.DataFrame()
      work_kpi["G_clean"] = kpi_df[g_col_name].apply(clean_code)
      work_kpi["F_clean"] = (
          kpi_df[f_col_name].astype(str).str.strip()
          if f_col_name in kpi_df.columns
          else ""
      )
      work_kpi["B_clean"] = (
          kpi_df[b_col_name].astype(str).str.strip()
          if b_col_name in kpi_df.columns
          else ""
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

      e_money_map = {}
      if wallet_report_sheet_name:
        try:
          w_rep_df = pd.read_excel(
              excel_file_obj, sheet_name=wallet_report_sheet_name
          )
          h_col = (
              w_rep_df.columns[7]
              if len(w_rep_df.columns) > 7
              else w_rep_df.columns[0]
          )
          r_col = (
              w_rep_df.columns[17]
              if len(w_rep_df.columns) > 17
              else w_rep_df.columns[-1]
          )
          e_col = (
              w_rep_df.columns[4]
              if len(w_rep_df.columns) > 4
              else w_rep_df.columns[0]
          )

          filtered_w = w_rep_df[
              w_rep_df[h_col].astype(str).str.strip().str.lower()
              == "organization e-money account".lower()
          ].copy()

          def clean_r_val(val):
            if pd.isna(val):
              return 0.0
            try:
              return float(str(val).replace(",", "").strip())
            except:
              return 0.0

          filtered_w["clean_R"] = filtered_w[r_col].apply(clean_r_val)
          filtered_w["e_code_clean"] = filtered_w[e_col].apply(clean_code)

          grouped_e = filtered_w.groupby("e_code_clean")["clean_R"].sum()
          e_money_map = grouped_e.to_dict()
          st.success(
              f"✅ تمت فلترة الشيت ({wallet_report_sheet_name}) لـ Organization"
              f" E-Money Account بنجاح."
          )
        except Exception as e_w:
          st.warning(f"⚠️ تعذر تحليل شيت wallet report: {e_w}")

      has_rep_file = rep_uploaded_file is not None
      rep_map_dict = {}
      if has_rep_file:
        try:
          rep_df = pd.read_excel(rep_uploaded_file)
          rep_code_col, rep_name_col = None, None
          for col in rep_df.columns:
            c_low = str(col).lower()
            if "short" in c_low or "code" in c_low or "كود" in str(col):
              rep_code_col = col
            if "مندوب" in str(col) or "rep" in c_low or "اسم" in str(col):
              rep_name_col = col
          if not rep_code_col and len(rep_df.columns) > 0:
            rep_code_col = rep_df.columns[0]
          if not rep_name_col and len(rep_df.columns) > 1:
            rep_name_col = rep_df.columns
          if rep_code_col and rep_name_col:
            for _, rrow in rep_df.iterrows():
              c_val = clean_code(rrow[rep_code_col])
              n_val = str(rrow[rep_name_col]).strip()
              rep_map_dict[c_val] = n_val
        except Exception:
          has_rep_file = False

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
        g_clean_str = clean_code(g_v)
        row_item = {
            "Short Code (G)": g_clean_str,
            "Arabic Name (F)": f_v,
        }
        if has_rep_file:
          row_item["اسم المندوب"] = rep_map_dict.get(
              g_clean_str, "غير محدد"
          )

        # إضافة عمود Organization E-Money Account في مكان واضح متقدم
        e_val_raw = e_money_map.get(g_clean_str, 0.0)
        row_item["Organization E-Money Account"] = f"{e_val_raw:,.2f}"

        for op in target_ops:
          count_val = grp["B_clean"].str.lower() == op.lower()
          row_item[f"عدد ({op})"] = int(count_val.sum())

        b2b_mask = (
            grp["B_clean"].str.lower() == "business to business transfer"
        )
        total_b2b_sum = grp.loc[b2b_mask, "T_num"].sum()
        row_item["مجموع مبالغ Business to Business Transfer"] = (
            f"{int(total_b2b_sum):,}"
            if total_b2b_sum == int(total_b2b_sum)
            else f"{total_b2b_sum:,.2f}"
        )

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
      st.subheader("📋 نتيجة تقرير الـ KPI المحدث")
      st.dataframe(final_kpi_table, use_container_width=True)

      buffer_kpi = BytesIO()
      with pd.ExcelWriter(buffer_kpi, engine="openpyxl") as writer:
        final_kpi_table.to_excel(writer, index=False)
      buffer_kpi.seek(0)

      st.download_button(
          label="📥 تحميل تقرير KPI نهائي (Excel)",
          data=buffer_kpi,
          file_name="KPI_Report_With_Wallet_E_Money.xlsx",
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
      )

    except Exception as err:
      st.error(f"⚠️ خطأ أثناء معالجة ملف الـ KPI: {err}")
  else:
    st.info("📌 يرجى رفع ملف الإكسل الرئيسي لعرض النتائج.")
