import re

# ... داخل try بعد kpi_df = pd.read_excel(kpi_file):
                required_cols = ['H', 'F', 'B', 'T']
                missing_cols = [c for c in required_cols if c not in kpi_df.columns]
                
                if missing_cols:
                    st.error(f"الملف المرفق يفتقر للأعمدة التالية: {missing_cols}. تأكد أن الأعمدة مهيأة بالحروف H, F, B, T.")
                else:
                    work_df = kpi_df.copy()
                    
                    # تنظيف ذكي وشامل لعمود T (يستخرج الأرقام والسالب والعشري ويحذف العملات/الرموز/المسافات)
                    def clean_t_value(val):
                        if pd.isna(val):
                            return 0.0
                        s = str(val).replace(',', '').strip()
                        # استخراج أول رقم/سالب/عشري صحيح من النص
                        match = re.search(r'[-+]?\d*\.?\d+', s)
                        try:
                            return float(match.group(0)) if match else 0.0
                        except:
                            return 0.0

                    work_df['T_num'] = work_df['T'].apply(clean_t_value)
                    
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
                            
                        # 2. حساب B2B باستخدام contains للتقاط أي اختلاف طفيف في المسافات أو الأحرف الكبيرة/الصغيرة
                        b2b_mask = group['B_clean'].str.contains('business to business transfer', case=False, na=False)
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
