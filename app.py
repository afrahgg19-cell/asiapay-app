with kpi_tab:
  st.header("📈 لوحة مؤشرات الأداء (KPI)")
  st.markdown(
      "ارفع ملف الإكسل الخاص بهذا التقرير لاستخراج الشورت كود، الأسماء، عدد"
      " مرات كل عملية في عمود B، ومبلغ B2B من عمود T."
  )

  kpi_file = st.file_uploader(
      "اختر ملف الإكسل (KPI)...", type=["xlsx", "xls"], key="kpi_uploader"
  )

  if kpi_file is not None:
    try:
      kpi_df = pd.read_excel(kpi_file)

      # مرونة في تعرييف الأعمدة (لو كانت أسماء أو حروف، سيحاول مطابقتها أو استخدام الفهارس)
      cols_list = kpi_df.columns.tolist()
      h_col = (
          "H"
          if "H" in kpi_df.columns
          else (cols_list[7] if len(cols_list) > 7 else cols_list[0])
      )
      f_col = (
          "F"
          if "F" in kpi_df.columns
          else (cols_list[5] if len(cols_list) > 5 else cols_list[0])
      )
      b_col = (
          "B"
          if "B" in kpi_df.columns
          else (cols_list if len(cols_list) > 1 else cols_list[0])
      )
      t_col = (
          "T"
          if "T" in kpi_df.columns
          else (cols_list[19] if len(cols_list) > 19 else cols_list[-1])
      )

      # أو إذا كنت متأكداً 100% أن الأعمدة مسمّاة حرفياً H, F, B, T في إكسلك، يمكنك استخدام kpi_df[['H', 'F', 'B', 'T']] مباشرة
      required_cols = [h_col, f_col, b_col, t_col]
      missing_cols = [c for c in required_cols if c not in kpi_df.columns]

      if missing_cols:
        st.error(
            f"الملف المرفق يفتقر للأعمدة المطلوبة: {missing_cols}. تأكد أن"
            " الأعمدة مطابقة."
        )
      else:
        work_df = kpi_df.copy()

        # تنظيف وتحويل عمود T إلى رقم
        work_df["T_num"] = pd.to_numeric(
            work_df[t_col].astype(str).str.replace(",", "").str.strip(),
            errors="coerce",
        ).fillna(0)

        # تنظيف عمود B وعمود H و F
        work_df["H_clean"] = work_df[h_col].astype(str).str.strip()
        work_df["F_clean"] = work_df[f_col].astype(str).str.strip()
        work_df["B_clean"] = work_df[b_col].astype(str).str.strip()

        kpi_results = []

        # تجميع حسب H و F
        for (h_val, f_val), group in work_df.groupby(
            ["H_clean", "F_clean"], dropna=False
        ):
          row_data = {"Short Code (H)": h_val, "الاسم بالعربي (F)": f_val}

          # 1. عد مرات كل نوع عملية في عمود B
          b_counts = group["B_clean"].value_counts()
          for op_type, count_val in b_counts.items():
            row_data[f"عدد ({op_type})"] = int(count_val)

          # 2. استخراج مجموع amount من عمود T لعمليات Business to business transfer
          b2b_mask = group["B_clean"].str.lower().str.contains(
              "business to business transfer", na=False
          ) | (group["B_clean"].str.lower() == "business to business transfer")
          b2b_amount = group.loc[b2b_mask, "T_num"].sum()
          row_data["مبلغ B2B (من T)"] = float(b2b_amount)

          kpi_results.append(row_data)

        kpi_summary_df = pd.DataFrame(kpi_results).fillna(0)

        st.subheader("📊 جدول نتائج الـ KPI")
        st.dataframe(kpi_summary_df, use_container_width=True)

        # خيار لتنزيل النتائج
        csv_data = kpi_summary_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 تحميل تقرير KPI (CSV)",
            data=csv_data,
            file_name="kpi_report_summary.csv",
            mime="text/csv",
        )

    except Exception as e:
      st.error(f"حصل خطأ أثناء معالجة ملف KPI: {e}")
