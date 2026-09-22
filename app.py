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
      st.success("✅ تم دمج ومعالجة ملفات المقارنة بنجاح!")
    except Exception as e:
      st.error(f"⚠️ خطأ: {e}")

  if st.session_state.get("combined_df") is not None:
    st.dataframe(st.session_state["combined_df"].head(50), use_container_width=True)


# ====================================================
# القسم الثالث: نسبة الإنجاز
# ====================================================
with tab3:
  st.markdown("### ⭐ نسبة الإنجاز والتقييم")
  if st.session_state.get("combined_df") is not None:
    st.info("البيانات جاهزة للتقييم.")
  else:
    st.info("يرجى رفع ملفات المقارنة أولاً.")


# ====================================================
# التبويب الرابع: KPI (مع المندوبين + Done للشروط + رصيد Organization E-Money Account مع فواصل عشرية)
# ====================================================
with tab_kpi:
  st.markdown("### 📈 لوحة مؤشرات الأداء (KPI)")
  st.write(
      "1. رفـع ملف الحركات الأساسي (إجباري - يدعم شيت Wallet Reports لو موجود أو"
      " الشيت الرئيسي).\n2. رفـع ملف المندوبين (اختياري)."
  )

  col_k1, col_k2, col_k3 = st.columns(3)
  with col_k1:
    kpi_uploaded_file = st.file_uploader(
        "اختر ملف الحركات (Excel)", type=["xlsx", "xls"], key="kpi_main_v6"
    )
  with col_k2:
    rep_uploaded_file = st.file_uploader(
        "اختر ملف المندوبين (اختياري)",
        type=["xlsx", "xls"],
        key="kpi_rep_v6",
    )
  with col_k3:
    wallet_report_sheet_choice = st.text_input(
        "اسم شيت Wallet Reports (اختياري، ترك فارغ للبحث التلقائي)", value=""
    )

  if kpi_uploaded_file is not None:
    try:
      xl_file = pd.ExcelFile(kpi_uploaded_file)
      sheet_to_use = xl_file.sheet_names[0]
      if (
          wallet_report_sheet_choice
          and wallet_report_sheet_choice in xl_file.sheet_names
      ):
        sheet_to_use = wallet_report_sheet_choice
      else:
        for s in xl_file.sheet_names:
          if "wallet" in s.lower() or "report" in s.lower():
            sheet_to_use = s
            break

      kpi_df = pd.read_excel(kpi_uploaded_file, sheet_name=sheet_to_use)

      def get_col_safe(preferred_name, fallback_idx, df_target):
        if preferred_name in df_target.columns:
          return preferred_name
        cols_local = [str(c).strip() for c in df_target.columns.tolist()]
        if len(cols_local) > fallback_idx:
          return df_target.columns[fallback_idx]
        return df_target.columns[0] if len(cols_local) > 0 else None

      g_col_name = get_col_safe("Short Code", 6, kpi_df)
      f_col_name = get_col_safe("Arabic Name", 5, kpi_df)
      b_col_name = get_col_safe("B", 1, kpi_df)
      t_col_name = get_col_safe("T", 19, kpi_df)
      h_col_name = get_col_safe("H", 7, kpi_df)
      r_col_name = get_col_safe("R", 17, kpi_df)

      work_kpi = pd.DataFrame()
      work_kpi["G_clean"] = (
          kpi_df[g_col_name].astype(str).str.strip()
          if g_col_name in kpi_df.columns
          else pd.Series([""] * len(kpi_df))
      )
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
      work_kpi["H_clean"] = (
          kpi_df[h_col_name].astype(str).str.strip()
          if h_col_name in kpi_df.columns
          else pd.Series([""] * len(kpi_df))
      )

      # تنظيف عمود T (المخزن كنص أو أرقام مع فاصلة أو مسافات)
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

      # تنظيف عمود R (Balance المخزن كنص/أرقام)
      raw_r_series = (
          kpi_df[r_col_name].astype(str)
          if r_col_name in kpi_df.columns
          else pd.Series(["0"] * len(kpi_df))
      )
      cleaned_r_numeric = (
          raw_r_series.str.replace(",", "", regex=False)
          .str.replace(" ", "", regex=False)
          .str.replace("$", "", regex=False)
      )
      work_kpi["R_num"] = pd.to_numeric(
          cleaned_r_numeric, errors="coerce"
      ).fillna(0.0)

      # ربط المندوبين
      has_rep_file = rep_uploaded_file is not None
      rep_map_dict = {}
      if has_rep_file:
        try:
          rep_df = pd.read_excel(rep_uploaded_file)
          rep_code_col, rep_name_col = None, None
          for col in rep_df.columns:
            c_low = str(col).lower()
            if (
                "short" in c_low
                or "code" in c_low
                or "كود" in str(col)
                or "short code" in c_low
            ):
              rep_code_col = col
            if (
                "مندوب" in str(col)
                or "representative" in c_low
                or "rep" in c_low
                or "اسم" in str(col)
            ):
              rep_name_col = col
          if not rep_code_col and len(rep_df.columns) > 0:
            rep_code_col = rep_df.columns[0]
          if not rep_name_col and len(rep_df.columns) > 1:
            rep_name_col = rep_df.columns
          if rep_code_col and rep_name_col:
            for _, rrow in rep_df.iterrows():
              c_val = str(rrow[rep_code_col]).strip()
              n_val = str(rrow[rep_name_col]).strip()
              rep_map_dict[c_val] = n_val
          st.success("✅ تم ربط أسماء المندوبين بنجاح.")
        except Exception as e_rep:
          st.warning(f"⚠️ تعذر قراءة ملف المندوبين: {e_rep}")
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
        row_item = {"Short Code (G)": g_v}
        if has_rep_file:
          row_item["اسم المندوب"] = rep_map_dict.get(
              str(g_v).strip(), "غير محدد"
          )
        row_item["Arabic Name (F)"] = f_v

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

        # عمودي شروط B2B
        row_item["حركه ال100 الف"] = (
            "Done" if total_b2b_sum > 99000 else ""
        )
        row_item["حركه ال3 مليون"] = (
            "Done" if total_b2b_sum > 2999000 else ""
        )

        # شرط عدد الحركات بمبلغ أكثر من 4,999 من عمود T
        high_t_count = int((grp["T_num"] > 4999).sum())
        row_item["عدد الحركات > 4999 (4+)"] = (
            "Done" if high_t_count >= 4 else ""
        )

        # استخراج رصيد Organization E-Money Account من عمود H وتنسيق Balance من عمود R بفواصل عشرية دقيقة
        emoney_mask = (
            grp["H_clean"].str.lower().str.strip()
            == "organization e-money account"
        )
        sub_emoney = grp.loc[emoney_mask]
        if not sub_emoney.empty:
          last_e_balance = sub_emoney.iloc[-1]["R_num"]
          # تحويل دقيق بفواصل عشرية (مثلاً: 123,456.78)
          row_item["رصيد Organization E-Money Account (R)"] = (
              f"{last_e_balance:,.2f}"
          )
        else:
          row_item["رصيد Organization E-Money Account (R)"] = "0.00"

        kpi_rows_list.append(row_item)

      final_kpi_table = pd.DataFrame(kpi_rows_list)
      st.subheader("📋 نتيجة تقرير الـ KPI النهائي")
      st.dataframe(final_kpi_table, use_container_width=True)

      out_kpi_name = (
          "KPI_Report_Complete_Ultimate.xlsx"
          if has_rep_file
          else "KPI_Report_Complete.xlsx"
      )
      buffer_kpi = BytesIO()

      df_to_save_kpi = final_kpi_table.copy()
      if isinstance(df_to_save_kpi.columns, pd.MultiIndex):
        df_to_save_kpi.columns = [
            "_".join([str(c) for c in col if c])
            for col in df_to_save_kpi.columns
        ]

      with pd.ExcelWriter(buffer_kpi, engine="openpyxl") as writer:
        df_to_save_kpi.to_excel(writer, index=False)
      buffer_kpi.seek(0)

      st.download_button(
          label="📥 تحميل تقرير KPI شامل مع الرصيد (Excel)",
          data=buffer_kpi,
          file_name=out_kpi_name,
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
          key="download_kpi_ultimate_v6_decimal",
      )

    except Exception as err:
      st.error(f"⚠️ خطأ أثناء معالجة ملف الـ KPI: {err}")
  else:
    st.info("📌 يرجى رفع ملف الإكسل الرئيسي للـ KPI على الأقل لعرض النتائج.")
