import pandas as pd
import streamlit as st

# إعداد الصفحة
st.set_page_config(
    page_title="تحليل العمليات والجرد", page_layout="wide", initial_sidebar_state="expanded"
)

st.title("📊 نظام تحليل ومقارنة الجرد والعمليات")

# إنشاء التبويبات
tab1, tab2, tab3 = st.tabs(
    ["📁 رفع وتحليل البيانات العامة", "🔢 أعداد العمليات لكل Short Code", "📈 مقارنة الشهور"]
)

# ====================================================
# التبويب الأول: رفع وتحليل البيانات العامة
# ====================================================
with tab1:
  st.subheader("📁 رفع ملفات البيانات الأساسية")
  uploaded_file_general = st.file_uploader(
      "اختر ملف الإكسل الرئيسي", type=["xlsx", "xls"], key="general_file"
  )
  if uploaded_file_general is not None:
    df_gen = pd.read_excel(uploaded_file_general)
    st.write("معاينة البيانات العامة:")
    st.dataframe(df_gen.head(), use_container_width=True)

# ====================================================
# التبويب الثاني: عدد العمليات لكل Short Code + عمود T
# ====================================================
with tab2:
  st.markdown("### 🔢 إحصائيات عدد العمليات لكل Short Code")
  st.write(
      "يتم عرض عدد العمليات لكل مكتب (Short Code) مع الاسم العربي (عمود F)،"
      " مع تحويل مبالغ العمود (T) إلى أرقام حقيقية."
  )

  uploaded_file_ops = st.file_uploader(
      "اختر ملف الإكسل الخاص بالعمليات (يحوي Short Code, Arabic Name, Reason"
      " وعمود T)",
      type=["xlsx", "xls"],
      key="file_ops_count",
  )

  if uploaded_file_ops is not None:
    try:
      df_ops = pd.read_excel(uploaded_file_ops)

      # الاعتماد على أسماء الأعمدة الظاهرة في صورتك أو الفهارس التقريبية
      # عمود H غالباً Short Code (index 7)، عمود F عربي (index 5)، عمود C أو غيره لنوع العمليات (Reason)
      # سنبحث عن الأعمدة بذكاء أو بالأسماء القياسية
      cols = df_ops.columns.tolist()

      # تحديد الأعمدة بناءً على الظاهر في صورتك:
      # C -> Reason, F -> Arabic Name, H -> Short Code, T -> index 19 (المبلغ المخزون كنص)
      code_col = (
          "Short Code"
          if "Short Code" in df_ops.columns
          else (cols[7] if len(cols) > 7 else cols)
      )
      name_col = (
          "Arabic Name"
          if "Arabic Name" in df_ops.columns
          else (cols[5] if len(cols) > 5 else cols[0])
      )
      reason_col = (
          "Reason 1"
          if "Reason 1" in df_ops.columns
          else ("Reason" if "Reason" in df_ops.columns else cols)
      )

      # معالجة العمود T (ترتيبه 20 في الإكسل أي index 19، أو البحث بحرف T/المبلغ)
      t_col_idx = 19
      t_col = (
          cols[t_col_idx]
          if len(cols) > t_col_idx
          else next(
              (c for c in cols if "t" in str(c).lower() or "amount" in str(c).lower()),
              cols,
          )
      )

      # تنظيف وتحويل عمود T إلى أرقام (number) بدلاً من نص
      if t_col in df_ops.columns:
        df_ops["Cleaned_T_Amount"] = (
            df_ops[t_col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.strip()
            .apply(
                lambda x: float(x)
                if x.replace(".", "", 1).replace("-", "", 1).isdigit()
                else 0.0
            )
        )
      else:
        df_ops["Cleaned_T_Amount"] = 0.0

      # ربط ثابث لاسم Short Code بالاسم العربي
      mapping_names = (
          df_ops.groupby(code_col)[name_col].first().to_dict()
          if code_col in df_ops.columns and name_col in df_ops.columns
          else {}
      )
      df_ops["الاسم_العربي_الموحد"] = df_ops[code_col].map(mapping_names)

      # خيار استثناء عملية معينة إذا رغبت (مثل العملية الثالثة أو أي نوع محدد من قائمة Reason)
      unique_reasons = (
          df_ops[reason_col].dropna().unique().tolist()
          if reason_col in df_ops.columns
          else []
      )
      excluded_reasons = st.multiselect(
          "اختر أنواع العمليات المراد استثناؤها (إن وجدت):",
          options=unique_reasons,
          default=[],
      )

      if excluded_reasons:
        df_ops = df_ops[~df_ops[reason_col].isin(excluded_reasons)]

      # حساب عدد العمليات لكل Short Code ونوع العملية
      if code_col in df_ops.columns and reason_col in df_ops.columns:
        ops_count_summary = (
            df_ops.groupby([code_col, "الاسم_العربي_الموحد", reason_col])
            .size()
            .reset_index(name="عدد_العمليات")
        )

        pivot_ops_count = ops_count_summary.pivot_table(
            index=[code_col, "الاسم_العربي_الموحد"],
            columns=reason_col,
            values="عدد_العمليات",
            aggfunc="sum",
            fill_value=0,
        ).reset_index()

        st.subheader("📋 جدول أعداد العمليات لكل Short Code حسب النوع")
        st.dataframe(pivot_ops_count, use_container_width=True)

        # مجموع المبالغ المحولة من عمود T لكل Short Code
        t_sum_summary = (
            df_ops.groupby([code_col, "الاسم_العربي_الموحد"])[
                "Cleaned_T_Amount"
            ]
            .sum()
            .reset_index(name="إجمالي_مبالغ_عمود_T_الرقمي")
        )

        final_merged = pd.merge(
            pivot_ops_count,
            t_sum_summary,
            on=[code_col, "الاسم_العربي_الموحد"],
            how="left",
        )
        st.subheader("💰 أعداد العمليات مع مجاميع مبالغ عمود T المحولة لأرقام")
        st.dataframe(final_merged, use_container_width=True)

        # زر التصدير
        out_file = "Operations_Count_Report.xlsx"
        final_merged.to_excel(out_file, index=False)
        with open(out_file, "rb") as f:
          st.download_button(
              "📥 تحميل تقرير أعداد العمليات (Excel)",
              data=f,
              file_name=out_file,
              mime=(
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              ),
          )
      else:
        st.error("لم يتم العثور على أعمدة Short Code أو Reason المطلوبة بدقة.")

    except Exception as e:
      st.error(f"حدث خطأ أثناء قراءة الملف: {e}")

# ====================================================
# التبويب الثالث: مقارنة الشهور
# ====================================================
with tab3:
  st.subheader("📈 مقارنة الشهور والجرد الكلي")
  st.write("مقارنة البيانات بين الشهور المختلفة...")
