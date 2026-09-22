# --- فرضاَ لديك الـ tabs الرئيسية هكذا:
# tab1, tab2, tab3, kpi_tab = st.tabs(["القسم الأول", "القسم الثاني", "القسم الثالث", "KPI"])

with kpi_tab:
    st.header("📈 لوحة مؤشرات الأداء (KPI)")
    st.markdown("ارفع ملف الإكسل الخاص بهذا التقرير لاستخراج الشورت كود، الأسماء، عدد مرات كل عملية في عمود B، ومبلغ B2B من عمود T.")
    
    kpi_file = st.file_uploader("اختر ملف الإكسل (KPI)...", type=["xlsx", "xls"], key="kpi_uploader")
    
    if kpi_file is not None:
        try:
            # قراءة الإكسل المرفوع للـ KPI
            kpi_df = pd.read_excel(kpi_file)
            
            # التأكد من وجود الأعمدة المطلوبة (H, F, B, T)
            # ملاحظة: إذا الأعمدة عندك تأتي بأسماء عناوين صفحة أو حروف أعمدة صريحة
            # سنفترض أن الأعمدة مسماة بالحروف أو تطابق الأسماء الفعليّة، سوينا معالجة مرنة:
            required_cols = ['H', 'F', 'B', 'T']
            
            # تحويل أسماء الأعمدة إلى حروف أو التأكد منها (لو الإكسل يحتوي عناوين عربية/إنجليزية، عدل حسب رغبتك، هنا نفترض الأعمدة H, F, B, T موجودة أو فهارس حروفية)
            # لنفترض أن الأسماء حرفية أو يتم البحث عنها، سنعالج الآتي:
            missing_cols = [c for c in required_cols if c not in kpi_df.columns]
            
            if missing_cols:
                st.error(f"الملف المرفق يفتقر للأعمدة التالية: {missing_cols}. تأكد أن الأعمدة مهيأة بالحروف H, F, B, T.")
            else:
                work_df = kpi_df.copy()
                
                # تنظيف وتحويل عمود T إلى رقم
                work_df['T_num'] = pd.to_numeric(
                    work_df['T'].astype(str).str.replace(',', '').str.strip(), 
                    errors='coerce'
                ).fillna(0)
                
                # تنظيف عمود B وعمود H و F
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
                    
                    # 1. عد مرات كل نوع عملية في عمود B
                    b_counts = group['B_clean'].value_counts()
                    for op_type, count_val in b_counts.items():
                        row_data[f"عدد ({op_type})"] = count_val
                        
                    # 2. باستثناء الـ Business to business transfer أو حساب الـ B2B كـ amount من T
                    # استخراج مجموع amount من عمود T لعمليات Business to business transfer
                    b2b_mask = group['B_clean'].str.lower() == 'business to business transfer'.lower()
                    b2b_amount = group.loc[b2b_mask, 'T_num'].sum()
                    row_data['مبلغ B2B (من T)'] = b2b_amount
                    
                    kpi_results.append(row_data)
                
                kpi_summary_df = pd.DataFrame(kpi_results).fillna(0)
                
                st.subheader("📊 جدول نتائج الـ KPI")
                st.dataframe(kpi_summary_df, use_container_width=True)
                
                # خيار لتنزيل النتائج
                csv_data = kpi_summary_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 تحميل تقرير KPI (CSV)",
                    data=csv_data,
                    file_name="kpi_report_summary.csv",
                    mime="text/csv"
                )
                
        except Exception as e:
            st.error(f حصل خطأ أثناء معالجة ملف KPI: {e}")
صح
