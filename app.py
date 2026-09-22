from io import BytesIO
import numpy as np
import pandas as pd
import streamlit as st

# إعدادات الصفحة
st.set_page_config(page_title="نظام تحليل التقارير والمحافظ", layout="wide")


# --- دوال مساعده عامة ---
def get_col_safe(col_name, default_idx, df):
  for c in df.columns:
    if str(c).strip().lower() == str(col_name).strip().lower():
      return c
  if default_idx < len(df.columns):
    return df.columns[default_idx]
  return col_name


def clean_office_code_column(df):
  # دالة تنظيف عامة لوضحت الحاجة
  return df


# إنشاء التبويبات الأربعة
tab1, tab2, tab3, tab_kpi = st.tabs([
    "التقرير الرئيسي (Transactions)",
    "تقرير المحافظ (Wallet Report)",
    "تقرير الوكلاء (Agent Report)",
    "KPI + رصيد المحفظة الدمج",
])

# ====================================================
# التبويب الأول: التقرير الرئيسي
# ====================================================
with tab1:
  st.subheader("📁 تحليل التقرير الرئيسي (Transaction Report)")
  f1 = st.file_uploader(
      "اختر ملف التقرير الرئيسي",
      type=["xlsx", "xls"],
      key="upload_tab1_main",
  )
  if f1 is not None:
    try:
      df1 = pd.read_excel(f1)
      st.write("عدد الأسطر:", len(df1))
      st.dataframe(df1.head(10), use_container_width=True)
    except Exception as e:
      st.error(f"خطأ: {e}")

# ====================================================
# التبويب الثاني: تقرير المحافظ
# ====================================================
with tab2:
  st.subheader("💳 تحليل تقرير المحافظ (Wallet Report)")
  f2 = st.file_uploader(
      "اختر ملف تقرير المحافظ", type=["xlsx", "xls"], key="upload_tab2_wallet"
  )
  if f2 is not None:
    try:
      df2 = pd.read_excel(f2)
      st.write("عدد الأسطر:", len(df2))
      st.dataframe(df2.head(10), use_container_width=True)
    except Exception as e:
      st.error(f"خطأ: {e}")

# ====================================================
# التبويب الثالث: تقرير الوكلاء
# ====================================================
with tab3:
  st.subheader("🏢 تحليل تقرير الوكلاء (Agent Report)")
  f3 = st.file_uploader(
      "اختر ملف تقرير الوكلاء", type=["xlsx", "xls"], key="upload_tab3_agent"
  )
  if f3 is not None:
    try:
      df3 = pd.read_excel(f3)
      st.write("عدد الأسطر:", len(df3))
      st.dataframe(df3.head(10), use_container_width=True)
    except Exception as e:
      st.error(f"خطأ: {e}")

# ====================================================
# التبويب الرابع: KPI + دمج عمود رصيد المحفظة (شيتين منفصلين أو ملف واحد)
# ====================================================
with tab_kpi:
  st.markdown("### 📈 لوحة مؤشرات الأداء (KPI) + ربط رصيد المحفظة")
  st.write(
      "يمكنك رفع **ملف الحركات (الرئيسي)** وملف **المحافظ (الاختياري/المحفظة)"
      "** بشكل منفصل أو ملف واحد يحتوي على الورقتين."
  )

  col_up1, col_up2 = st.columns(2)
  with col_up1:
    main_trans_file = st.file_uploader(
        "1. ملف الحركات الرئيسي (Transaction Report)",
        type=["xlsx", "xls"],
        key="kpi_main_trans_file",
    )
  with col_up2:
    optional_wallet_file = st.file_uploader(
        "2. ملف المحافظ الاختياري / الفرعي (Wallet Report)",
        type=["xlsx", "xls"],
        key="kpi_optional_wallet_file",
    )

  if main_trans_file is not None:
    try:
      # قراءة ملف الحركات
      excel_reader_main = pd.ExcelFile(main_trans_file)
      st.write(
          "أوراق ملف الحركات المتاح:", excel_reader_main.sheet_names
      )
      chosen_trans_sheet = st.selectbox(
          "اختر ورقة العمل الخاصة بالحركات الرئيسية:",
          excel_reader_main.sheet_names,
          key="sel_trans_sheet",
      )
      kpi_df = pd.read_excel(
          main_trans_file, sheet_name=chosen_trans_sheet
      )

      # قراءة ملف المحافظ الاختياري إن وجد، أو البحث بالملف نفسه
      wallet_source_df = None
      if optional_wallet_file is not None:
        excel_reader_opt = pd.ExcelFile(optional_wallet_file)
        chosen_opt_sheet = st.selectbox(
            "اختر ورقة العمل الخاصة بالمحافظ (من الملف الاختياري):",
            excel_reader_opt.sheet_names,
            key="sel_opt_sheet",
        )
        wallet_source_df = pd.read_excel(
            optional_wallet_file, sheet_name=chosen_opt_sheet
        )
        st.success("✅ تم اعتماد ملف المحافظ الاختياري المرفق بنجاح.")
      else:
        st.info(
            "ℹ️ لم يتم رفع ملف محافظ منفصل، سيتم البحث إن توفرت ورقة ثانية"
            " بنفس ملف الحركات أو الاكتفاء بالصفر إن لم يُعثر."
        )
        if len(excel_reader_main.sheet_names) > 1:
          wallet_source_df = kpi_df  # fallback أو ورقة أخرى

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

      # --- بناء قاموس مطابقة Short Code مع Balance (تنظيف صارم للنصوص والفواصل) ---
      opt_lookup = {}
      if wallet_source_df is not None:
        opt_code_col = None
        for c in wallet_source_df.columns:
          c_low = str(c).lower()
          if "short" in c_low and "code" in c_low:
            opt_code_col = c
            break
        if not opt_code_col and len(wallet_source_df.columns) > 0:
          opt_code_col = wallet_source_df.columns[0]

        balance_col_target = next(
            (
                c
                for c in wallet_source_df.columns
                if "balance" in str(c).lower() or "رصيد" in str(c)
            ),
            None,
        )

        def clean_bal_opt_strict(val):
          if pd.isna(val):
            return 0.0
          val_s = (
              str(val)
              .replace(",", "")
              .replace(" ", "")
              .replace("'", "")
              .strip()
          )
          try:
            return float(val_s)
          except:
            return 0.0

        for _, rrow in wallet_source_df.iterrows():
          c_key = (
              str(rrow[opt_code_col]).strip().replace(".0", "")
              if pd.notna(rrow[opt_code_col])
              else ""
          )
          if c_key:
            bal_val = (
                clean_bal_opt_strict(rrow[balance_col_target])
                if balance_col_target and balance_col_target in rrow
                else 0.0
            )
            opt_lookup[c_key] = bal_val

      st.success("✅ تمت معالجة البيانات والربط بنجاح.")

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

      st.subheader(
          "📋 نتيجة تقرير الـ KPI (مع عمود رصيد المحفظة الرقمي المدمج)"
      )
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
      st.error(f"⚠️ خطأ أثناء معالجة الملفات: {err}")
  else:
      st.info("📌 يرجى رفع ملف الحركات الرئيسي (على الأقل) لعرض وتحليل النتائج.")
