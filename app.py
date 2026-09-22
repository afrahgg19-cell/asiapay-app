import streamlit as st
import pandas as pd

# إعداد الصفحة
st.set_page_config(page_title="تطبيق التحدارة والأداء و KPI", layout="wide")

st.title("📊 نظام إدارة التقارير والجرد ومؤشرات الأداء")

# --- تعريف التبويبات (الأقسام القديمة + تبويب KPI الجديد) ---
tab1, tab2, tab3, tab_kpi = st.tabs([
    "القسم الأول (إدارة البيانات)", 
    "📊 الجرد الكلي ومقارنة الشهور", 
    "⭐ نسب الأداء", 
    "KPI"
])

# ==========================================
# 1. القسم الأول (نصياً كما هو / ضع كودك القديم هنا)
# ==========================================
with tab1:
    st.header("القسم الأول")
    st.info("ضع محتوى القسم الأول القديم هنا نصاً بدون تعديل.")
    # مثال هيكلي قد يكون موجود لديك:
    # uploaded_file_1 = st.file_uploader("رفع ملف القسم الأول...", type=["xlsx", "csv"], key="file1")

# ==========================================
# 2. القسم الثاني (📊 الجرد الكلي ومقارنة الشهور)
# ==========================================
with tab2:
    st.header("📊 الجرد الكلي ومقارنة الشهور")
    st.info("ضع محتوى القسم الثاني القديم هنا نصاً بدون تعديل.")
    # مثال: استرجاع من session_state إن وجد أو وضع المنطق القديم
    if "pivot_result" in st.session_state:
        st.write(st.session_state["pivot_result"])

# ==========================================
# 3. القسم الثالث (⭐ نسب الأداء)
# ==========================================
with tab3:
    st.header("⭐ نسب الأداء")
    st.info("ضع محتوى القسم الثالث القديم هنا نصاً بدون تعديل.")
    if "perf_summary" in st.session_state:
        st.write(st.session_state["perf_summary"])

# ==========================================
# 4. تبويب الـ KPI الجديد (حسب الطلب تماماً)
# ==========================================
with tab_kpi:
    st.header("📈 لوحة مؤشرات الأداء (KPI)")
    st.markdown("ارفع ملف الإكسل (يجب أن يحتوي أعمدة **H** كـ short code، **F** للأسماء بالعربي، **B** لنوع العمليات، **T** للمبالغ).")
    
    kpi_file = st.file_uploader("اختر ملف إكسل للـ KPI...", type=["xlsx", "xls"], key="kpi_main_uploader")
    
    if kpi_file is not None:
        try:
            kpi_df = pd.read_excel(kpi_file)
            
            required_cols = ['H', 'F', 'B', 'T']
            missing_cols = [c for c in required_cols if c not in kpi_df.columns]
            
            if missing_cols:
                st.error(f"❌ الأعمدة التالية مفقودة في الملف المرفق: {missing_cols}. تأكد من تسمية الأعمدة بحروف H, F, B, T.")
            else:
                work_df = kpi_df.copy()
                
                # تحويل عمود T إلى نمبر (رقم) بعد تنظيف النصوص والفواصل
                work_df['T_num'] = pd.to_numeric(
                    work_df['T'].astype(str).str.replace(',', '').str.strip(), 
                    errors='coerce'
                ).fillna(0)
                
                # تنظيف النصوص للأعمدة الأساسية
                work_df['H_clean'] = work_df['H'].astype(str).str.strip()
                work_df['F_clean'] = work_df['F'].astype(str).str.strip()
                work_df['B_clean'] = work_df['B'].astype(str).str.strip()
                
                kpi_results = []
                
                # تجميع حسب H و F
                for (h_val, f_val), group in work_df.groupby(['H_clean', 'F_clean'], dropna=False):
                    row_data = {
                        'Short Code (H)': h_val,
                        'الاسم بالعربي (F)': f_val
                    }
                    
                    # عدد مرات كل عملية من عمود B (عدد وليس مبلغ)
                    b_counts = group['B_clean'].value_counts()
                    for op_type, count_val in b_counts.items():
                        row_data[f"عدد ({op_type})"] = count_val
                        
                    # باستثناء/استخراج الـ Business to business transfer كمبلغ من عمود T
                    b2b_mask = group['B_clean'].str.lower() == 'business to business transfer'.lower()
                    b2b_amount_t = group.loc[b2b_mask, 'T_num'].sum()
                    row_data['مبلغ B2B (من T)'] = b2b_amount_t
                    
                    kpi_results.append(row_data)
                
                # بناء الجدول النهائي وتعويض الفراغات بأصفار
                kpi_summary_df = pd.DataFrame(kpi_results).fillna(0)
                
                st.subheader("📋 نتيجة تجميع الـ KPI")
                st.dataframe(kpi_summary_df, use_container_width=True)
                
                # زر تحميل النتائج
                csv_export = kpi_summary_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 تحميل تقرير KPI نهائي (CSV)",
                    data=csv_export,
                    file_name="kpi_summary_report.csv",
                    mime="text/csv"
                )
                
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة ملف الـ KPI: {e}")
