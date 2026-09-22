import re
import pandas as pd
import streamlit as st

# إعداد الصفحة
st.set_page_config(
    page_title="نظام الإدارة والتقارير الشامل",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 نظام إدارة المخزون، المبيعات ومؤشرات الأداء (B2B)")

# إنشاء التبويبات الرئيسية للتطبيق
tab_inv, tab_sales, tab_kpi = st.tabs(
    ["📦 المخزون", "💰 المبيعات والمصروفات", "📈 مؤشرات الأداء (KPI)"]
)

# ---------------------------------------------------------
# تبويب 1: المخزون
# ---------------------------------------------------------
with tab_inv:
  st.subheader("إدارة المخزون")
  inv_file = st.file_uploader(
      "رفع ملف المخزون", type=["xlsx", "csv"], key="inv_uploader"
  )
  if inv_file is not None:
    try:
      df_inv = (
          pd.read_excel(inv_file)
          if inv_file.name.endswith(".xlsx")
          else pd.read_csv(inv_file)
      )
      st.dataframe(df_inv, use_container_width=True)
    except Exception as e:
      st.error(f"خطأ في قراءة ملف المخزون: {e}")
  else:
    st.info("يرجى رفع ملف المخزون لعرض البيانات.")

# ---------------------------------------------------------
# تبويب 2: المبيعات والمصروفات
# ---------------------------------------------------------
with tab_sales:
  st.subheader("إدارة المبيعات والمصروفات")
  sales_file = st.file_uploader(
      "رفع ملف المبيعات/المصروفات", type=["xlsx", "csv"], key="sales_uploader"
  )
  if sales_file is not None:
    try:
      df_sales = (
          pd.read_excel(sales_file)
          if sales_file.name.endswith(".xlsx")
          else pd.read_csv(sales_file)
      )
      st.dataframe(df_sales, use_container_width=True)
    except Exception as e:
      st.error(f"خطأ في قراءة ملف المبيعات: {e}")
  else:
    st.info("يرجى رفع ملف المبيعات لعرض البيانات.")

# ---------------------------------------------------------
# تبويب 3: مؤشرات الأداء (KPI) ومعالجة B2B
# ---------------------------------------------------------
with tab_kpi:
  st.markdown("### 📈 لوحة مؤشرات الأداء (KPI)")
  st.write(
      "تجميع Short Code (عمود H)، الاسم بالعربي (عمود F)، عد العمليات"
      " من عمود C، واستخراج مبالغ B2B من عمود T النصي."
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

      h_idx = 7 if len(cols_list) > 7 else 0
      f_idx = 5 if len(cols_list) > 5 else 0
      c_idx = 2 if len(cols_list) > 2 else 0
      t_idx = (
          kpi_df.columns.get_loc("Amount")
          if "Amount" in kpi_df.columns
          else (19 if len(cols_list) > 19 else len(cols_list) - 1)
      )

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

      # استخراج عمود T النصي بدقة
      raw_t_series = (
          kpi_df["T"].astype(str)
          if "T" in kpi_df.columns
          else kpi_df.iloc[:, t_idx].astype(str)
      )
      work_kpi["T_text"] = raw_t_series.str.strip()

      # تنظيف واستخراج الأرقام الحقيقية من النصوص المعقدة في عمود T
      def extract_number_from_text(val):
        if pd.isna(val):
          return 0.0
        val_str = str(val).replace(",", "").replace(" ", "")
        match = re.search(r"[-+]?\d*\.?\d+", val_str)
        if match:
          try:
            return float(match.group(0))
          except:
            return 0.0
        return 0.0

      work_kpi["T_num"] = work_kpi["T_text"].apply(extract_number_from_text)

      kpi_rows_list = []
      for (h_v, f_v), grp in work_kpi.groupby(
          ["H_clean", "F_clean"], dropna=False
      ):
        row_item = {
            "Short Code (H)": h_v,
            "Arabic Name (F)": f_v,
        }

        c_value_counts = grp["C_clean"].value_counts()
        for op_name, op_count in c_value_counts.items():
          row_item[f"عدد ({op_name})"] = op_count

        # مطابقة مرنة لعمليات B2B في عمود C
        b2b_mask = grp["C_clean"].str.contains(
            "business to business", case=False, na=False
        )

        b2b_total_num = grp.loc[b2b_mask, "T_num"].sum()
        b2b_texts = [
            t
            for t in grp.loc[b2b_mask, "T_text"].tolist()
            if str(t).lower() not in ["nan", "none", "", "nat"]
        ]

        row_item["مجموع مبالغ B2B (رقمي محول من T)"] = b2b_total_num
        row_item["نصوص B2B الأصلية (T)"] = (
            " | ".join(set(b2b_texts)) if b2b_texts else "لا يوجد"
        )

        kpi_rows_list.append(row_item)

      final_kpi_table = pd.DataFrame(kpi_rows_list).fillna(0)
      st.subheader("📋 نتيجة تقرير الـ KPI")
      st.dataframe(final_kpi_table, use_container_width=True)

      # أداة فحص سريعة للتأكد من قراءة العمود T والمبالغ
      with st.expander("🔍 فحص القيم المستخرجة من عمود T و C"):
        st.dataframe(
            work_kpi[work_kpi["C_clean"].str.contains("business", case=False)][
                ["C_clean", "T_text", "T_num"]
            ].head(30),
            use_container_width=True,
        )

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
