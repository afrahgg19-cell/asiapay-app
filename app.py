from io import BytesIO
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="نظام إدارة المحفظة المالية الكبرى - ASIA PAY", layout="wide"
)

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

# يمكنك إبقاء الكود السابق للتبويب الأول والثاني والثالث كما هو، والتركيز على تبويب KPI المعدل أدناه:

with tab_kpi:
  st.markdown("### 📈 لوحة مؤشرات الأداء (KPI) + رصيد المحفظة")
  st.write(
      "ارفع **ملف الإكسل** (يحتوي على الأوراق المطلوبة، وخصوصاً ورقة"
      " 'Wallet report')."
  )

  col_k1, col_k2 = st.columns(2)
  with col_k1:
    kpi_uploaded_file = st.file_uploader(
        "اختر ملف الإكسل الرئيسي", type=["xlsx", "xls"], key="kpi_main_fixed"
    )
  with col_k2:
    rep_uploaded_file = st.file_uploader(
        "اختر ملف المندوبين (اختياري)",
        type=["xlsx", "xls"],
        key="kpi_rep_fixed",
    )

  if kpi_uploaded_file is not None:
    try:
      excel_file_obj = pd.ExcelFile(kpi_uploaded_file)
      sheet_names = excel_file_obj.sheet_names
      st.info(f"📁 الأوراق المكتشفة داخل الملف: {sheet_names}")

      # تحديد ورقة الحركات (الورقة الأولى أو الافتراضية)
      kpi_df = pd.read_excel(kpi_uploaded_file, sheet_name=0)

      # البحث عن ورقة Wallet report أو استخدام الورقة الثانية
      wallet_balance_map = {}
      wallet_sheet_name = None
      for s in sheet_names:
        if "wallet" in s.lower():
          wallet_sheet_name = s
          break
      if not wallet_sheet_name and len(sheet_names) > 1:
        wallet_sheet_name = sheet_names

      if wallet_sheet_name:
        w_df = pd.read_excel(kpi_uploaded_file, sheet_name=wallet_sheet_name)
        st.caption(
            f"✅ يتم قراءة رصيد المحفظة من الورقة: '{wallet_sheet_name}'"
        )

        # البحث عن أعمدة accountType (H تقريباً)، balance (R)، والشورت كود في العمود E
        h_col_w = next(
            (c for c in w_df.columns if "accounttype" in str(c).lower()), None
        )
        r_col_w = next(
            (c for c in w_df.columns if "balance" in str(c).lower()), None
        )
        # العمود E هو غالباً الفهرس 4 (A=0, B=1, C=2, D=3, E=4) أو يبحث عن shortCode
        e_col_w = next(
            (
                c
                for c in w_df.columns
                if str(c).strip().lower()
                in ["shortcode", "short code", "short_code", "e"]
            ),
            None,
        )
        if not e_col_w and len(w_df.columns) > 4:
          e_col_w = w_df.columns  # العمود الخامس E
        if not h_col_w and len(w_df.columns) > 7:
          h_col_w = w_df.columns
        if not r_col_w and len(w_df.columns) > 17:
          r_col_w = w_df.columns[17]

        if h_col_w and r_col_w and e_col_w:
          mask_h = (
              w_df[h_col_w].astype(str).str.strip()
              == "Organization E-Money Account"
          )
          filtered_w = w_df[mask_h].copy()

          def clean_balance_val(val):
            if pd.isna(val):
              return 0.0
            s = str(val).strip()
            if not s:
              return 0.0
            neg = False
            if s.startswith("(") and s.endswith(")"):
              neg = True
              s = s[1:-1].strip()
            s = s.replace(",", "")
            try:
              num = float(s)
              return -num if neg else num
            except ValueError:
              return 0.0

          filtered_w["cleaned_R"] = filtered_w[r_col_w].apply(
              clean_balance_val
          )
          filtered_w["key_clean"] = (
              filtered_w[e_col_w].astype(str).str.strip().str.upper()
          )

          wallet_balance_map = (
              filtered_w.groupby("key_clean")["cleaned_R"].sum().to_dict()
          )
          st.success("✅ تمت مطابقة وتجميع أرصدة المحفظة حسب الشورت كود في العمود E بنجاح!")
        else:
          st.warning("⚠️ لم يتم العثور على أعمدة التطابق المطلوبة بدقة في ورقة المحفظة.")

      # تجهيز أعمدة الحركات (الشورت كود في العمود E أو G حسب الملف، سنبحث عن العمود E أو shortCode)
      e_col_name = next(
          (
              c
              for c in kpi_df.columns
              if str(c).strip().lower()
              in ["shortcode", "short code", "short_code"]
          ),
          None,
      )
      if not e_col_name and len(kpi_df.columns) > 4:
        e_col_name = kpi_df.columns  # العمود E افتراضياً

      f_col_name = next(
          (c for c in kpi_df.columns if "arabic name" in str(c).lower()), None
      )
      if not f_col_name and len(kpi_df.columns) > 5:
        f_col_name = kpi_df.columns

      b_col_name = next(
          (c for c in kpi_df.columns if "type" in str(c).lower() and c != e_col_name), None
      )
      if not b_col_name and len(kpi_df.columns) > 1:
        b_col_name = kpi_df.columns

      t_col_name = next(
          (c for c in kpi_df.columns if "amount" in str(c).lower() or "t" == str(c).lower()), None
      )
      if not t_col_name and len(kpi_df.columns) > 19:
        t_col_name = kpi_df.columns[19]

      work_kpi = pd.DataFrame()
      work_kpi["E_clean"] = (
          kpi_df[e_col_name].astype(str).str.strip().str.upper()
          if e_col_name in kpi_df.columns
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

      # ربط المندوبين
      has_rep_file = rep_uploaded_file is not None
      rep_map_dict = {}
      if has_rep_file:
        try:
          rep_df = pd.read_excel(rep_uploaded_file)
          rep_code_col = rep_df.columns[0]
          rep_name_col = rep_df.columns if len(rep_df.columns) > 1 else rep_df.columns[0]
          for _, rrow in rep_df.iterrows():
            c_val = str(rrow[rep_code_col]).strip().upper()
            n_val = str(rrow[rep_name_col]).strip()
            rep_map_dict[c_val] = n_val
        except Exception:
          pass

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
      for (e_v, f_v), grp in work_kpi.groupby(["E_clean", "F_clean"], dropna=False):
        row_item = {"Short Code (E)": e_v}
        if has_rep_file:
          row_item["اسم المندوب"] = rep_map_dict.get(str(e_v).strip().upper(), "غير محدد")
        row_item["Arabic Name (F)"] = f_v

        g_str_key = str(e_v).strip().upper()
        # جلب الرصيد المطابق أو 0 بدلاً من النص الفارغ لكي تظهر الأرقام
        wallet_val = wallet_balance_map.get(g_str_key, 0.0)
        row_item["رصيد المحفظة"] = (
            f"{wallet_val:,.2f}" if isinstance(wallet_val, (int, float, np.number)) else wallet_val
        )

        for op in target_ops:
          count_val = grp["B_clean"].str.lower() == op.lower()
          row_item[f"عدد ({op})"] = int(count_val.sum())

        b2b_mask = grp["B_clean"].str.lower() == "business to business transfer"
        total_b2b_sum = grp.loc[b2b_mask, "T_num"].sum()
        row_item["مجموع مبالغ B2B"] = (
            f"{int(total_b2b_sum):,}" if total_b2b_sum == int(total_b2b_sum) else f"{total_b2b_sum:,.2f}"
        )

        row_item["حركه ال100 الف"] = "Done" if total_b2b_sum > 99000 else ""
        row_item["حركه ال3 مليون"] = "Done" if total_b2b_sum > 2999000 else ""

        high_t_count = int((grp["T_num"] > 4999).sum())
        row_item["عدد الحركات > 4999 (4+)"] = "Done" if high_t_count >= 4 else ""

        kpi_rows_list.append(row_item)

      final_kpi_table = pd.DataFrame(kpi_rows_list)
      st.subheader("📋 نتيجة تقرير الـ KPI النهائي")
      st.dataframe(final_kpi_table, use_container_width=True)

      buffer_kpi = BytesIO()
      with pd.ExcelWriter(buffer_kpi, engine="openpyxl") as writer:
        final_kpi_table.to_excel(writer, index=False)
      buffer_kpi.seek(0)

      st.download_button(
          label="📥 تحميل تقرير KPI النهائي (Excel)",
          data=buffer_kpi,
          file_name="KPI_Report_Fixed.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      )

    except Exception as err:
      st.error(f"⚠️ خطأ أثناء معالجة الملف: {err}")
