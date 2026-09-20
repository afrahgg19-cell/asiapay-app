import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="نظام متابعة المشاريع ونسب الإنجاز", layout="wide"
)

st.title("📊 نظام متابعة المشاريع ومقارنة نسب الإنجاز الشهري")
st.markdown("---")

DATA_FILE = "projects_data.csv"


def load_data():
  try:
    df = pd.read_csv(DATA_FILE)
    return df
  except Exception:
    # إنشاء قالب افتراضي إذا لم يكن الملف موجوداً
    return pd.DataFrame(
        columns=[
            "اسم المشروع",
            "الشهر",
            "نسبة الإنجاز (%)",
            "الميزانية المخصصة",
            "المبلغ المصروف",
            "الحالة",
        ]
    )


df = load_data()

# الشريط الجانبي للإدخال
st.sidebar.header("➕ إضافة / تحديث بيانات مشروع")
with st.sidebar.form("project_form", clear_on_submit=True):
  p_name = st.text_input("اسم المشروع")
  p_month = st.selectbox(
      "الشهر", [
          "يناير",
          "فبراير",
          "مارس",
          "أبريل",
          "مايو",
          "يونيو",
          "يوليو",
          "أغسطس",
          "سبتمبر",
          "أكتوبر",
          "نوفمبر",
          "ديسمبر",
      ]
  )
  p_progress = st.slider("نسبة الإنجاز (%)", 0, 100, 0)
  p_budget = st.number_input("الميزانية المخصصة (د.ع)", min_value=0.0, step=1000.0)
  p_spent = st.number_input("المبلغ المصروف (د.ع)", min_value=0.0, step=1000.0)
  p_status = st.selectbox(
      "حالة المشروع", ["مستمر", "متوقف", "مكتمل", "متأخر"]
  )

  submitted = st.form_submit_button("حفظ البيان")
  if submitted:
    if p_name:
      new_row = pd.DataFrame([{
          "اسم المشروع": p_name,
          "الشهر": p_month,
          "نسبة الإنجاز (%)": p_progress,
          "الميزانية المخصصة": p_budget,
          "المبلغ المصروف": p_spent,
          "الحالة": p_status,
      }])
      df = pd.concat([df, new_row], ignore_index=True)
      df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
      st.sidebar.success("تم إضافة بيانات المشروع بنجاح!")
      st.rerun()
    else:
      st.sidebar.warning("يرجى إدخال اسم المشروع على الأقل.")

# عرض البيانات العامة
st.subheader("📋 جدول البيانات الكلي")
if not df.empty:
  st.dataframe(df, use_container_width=True)
else:
  st.info("لا توجد بيانات مسجلة حتى الآن. استخدم القائمة الجانبية للإضافة.")

st.markdown("---")

# قسم مقارنة الشهور
st.subheader("📈 مقارنة نسب الإنجاز بين الشهور للمشاريع")
if not df.empty and "الشهر" in df.columns:
  unique_projects = df["اسم المشروع"].unique()
  selected_project = st.selectbox("اختر المشروع للمقارنة الشهرية:", unique_projects)

  proj_df = df[df["اسم المشروع"] == selected_project]
  if not proj_df.empty:
    st.write(f"### تطور إنجاز مشروع: {selected_project}")
    st.dataframe(
        proj_df[["الشهر", "نسبة الإنجاز (%)", "المبلغ المصروف", "الحالة"]],
        use_container_width=True,
    )
    # رسم بياني بسيط لنسب الإنجاز حسب الشهر
    chart_data = proj_df.set_index("الشهر")["نسبة الإنجاز (%)"]
    st.bar_chart(chart_data)
  else:
    st.warning("لا توجد بيانات لهذا المشروع.")

st.markdown("---")

# إحصائيات عامة
st.subheader("📊 ملخص عام نسب الإنجاز والأداء")
if not df.empty:
  col1, col2, col3 = st.columns(3)
  avg_progress = df["نسبة الإنجاز (%)"].mean()
  total_budget = df["الميزانية المخصصة"].sum()
  total_spent = df["المبلغ المصروف"].sum()

  col1.metric("متوسط نسب الإنجاز الكلي", f"{avg_progress:.1f} %")
  col2.metric("إجمالي الميزانيات", f"{total_budget:,.2f} د.ع")
  col3.metric("إجمالي المصاريف", f"{total_spent:,.2f} د.ع")
