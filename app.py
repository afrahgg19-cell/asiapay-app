from io import BytesIO
import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
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

      kpi_df = pd.read_excel(kpi_uploaded_file, sheet_name=0)

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

        h_col_w = next(
            (c for c in w_df.columns if "accounttype" in str(c).lower()), None
        )
        r_col_w = next(
            (c for c in w_df.columns if "balance" in str(c).lower()), None
        )
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
          e_col_w = w_df.columns
        if not h_col_w and len(w_df.columns) > 7:
          h_col_w = w_df.columns
        if not r_col_w and len(w_df.columns) > 17:
          r_col_w = w_df.columns[17]

        if h_col_w is not None and r_col_w is not None and e_col_w is not None:
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
          st.success(
              "✅ تمت مطابقة وتجميع أرصدة المحفظة حسب الشورت كود في العمود E"
              " بنجاح!"
          )
        else:
          st.warning(
              "⚠️ لم يتم العثور على أعمدة التطابق المطلوبة بدقة في ورقة المحفظة."
          )

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
        e_col_name = kpi_df.columns

      f_col_name = next(
          (c for c in kpi_df.columns if "arabic name" in str(c).lower()), None
      )
      if not f_col_name and len(kpi_df.columns) > 5:
        f_col_name = kpi_df.columns

      b_col_name = next(
          (
              c
              for c in kpi_df.columns
              if "type" in str(c).lower() and c != e_col_name
          ),
          None,
      )
      if not b_col_name and len(kpi_df.columns) > 1:
        b_col_name = kpi_df.columns

      t_col_name = next(
          (
              c
              for c in kpi_df.columns
              if "amount" in str(c).lower() or "t" == str(c).lower()
          ),
          None,
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

      has_rep_file = rep_uploaded_file is not None
      rep_map_dict = {}
      if has_rep_file:
        try:
          rep_df = pd.read_excel(rep_uploaded_file)
          rep_code_col = rep_df.columns[0]
          rep_name_col = (
              rep_df.columns if len(rep_df.columns) > 1 else rep_df.columns[0]
          )
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
      for (e_v, f_v), grp in work_kpi.groupby(
          ["E_clean", "F_clean"], dropna=False
      ):
        row_item = {"Short Code (E)": e_v}
        if has_rep_file:
          row_item["اسم المندوب"] = rep_map_dict.get(
              str(e_v).strip().upper(), "غير محدد"
          )
        row_item["Arabic Name (F)"] = f_v

        g_str_key = str(e_v).strip().upper()
        wallet_val = wallet_balance_map.get(g_str_key, 0.0)
        row_item["رصيد المحفظة"] = (
            f"{wallet_val:,.2f}"
            if isinstance(wallet_val, (int, float, np.number))
            else wallet_val
        )

        for op in target_ops:
          count_val = grp["B_clean"].str.lower() == op.lower()
          row_item[f"عدد ({op})"] = int(count_val.sum())

        b2b_mask = grp["B_clean"].str.lower() == "business to business transfer"
        total_b2b_sum = grp.loc[b2b_mask, "T_num"].sum()
        row_item["مجموع مبالغ B2B"] = (
            f"{int(total_b2b_sum):,}"
            if total_b2b_sum == int(total_b2b_sum)
            else f"{total_b2b_sum:,.2f}"
        )

        row_item["حركه ال100 الف"] = "Done" if total_b2b_sum > 99000 else ""
        row_item["حركه ال3 مليون"] = "Done" if total_b2b_sum > 2999000 else ""

        high_t_count = int((grp["T_num"] > 4999).sum())
        row_item["عدد الحركات > 4999 (4+)"] = (
            "Done" if high_t_count >= 4 else ""
        )

        kpi_rows_list.append(row_item)

      final_kpi_table = pd.DataFrame(kpi_rows_list)
      st.subheader("📋 نتيجة تقرير الـ KPI النهائي")
      st.dataframe(final_kpi_table, use_container_width=True)

      # تصدير مع تطبيق التنسيق المطلوب (حجم الخط 14، حدود شباك، تلوين رصاصي وأبيض)
      buffer_kpi = BytesIO()
      with pd.ExcelWriter(buffer_kpi, engine="openpyxl") as writer:
        final_kpi_table.to_excel(writer, index=False, sheet_name="KPI_Report")
        wb = writer.book
        ws = wb["KPI_Report"]

        # الأنماط المطلوبة
        header_font = Font(
            name="Calibri", size=14, bold=True, color="FFFFFF"
        )
        header_fill = PatternFill(
            start_color="595959", end_color="595959", fill_type="solid"
        )
        font_size_14 = Font(name="Calibri", size=14, bold=False, color="000000")
        light_gray_fill = PatternFill(
            start_color="F2F2F2", end_color="F2F2F2", fill_type="solid"
        )
        white_fill = PatternFill(
            start_color="FFFFFF", end_color="FFFFFF", fill_type="solid"
        )

        thin_border = Border(
            left=Side(style="thin", color="D9D9D9"),
            right=Side(style="thin", color="D9D9D9"),
            top=Side(style="thin", color="D9D9D9"),
            bottom=Side(style="thin", color="D9D9D9"),
        )

        for row_idx, row in enumerate(
            ws.iter_rows(
                min_row=1,
                max_row=ws.max_row,
                min_col=1,
                max_col=ws.max_column,
            ),
            start=1,
        ):
          for cell in row:
            cell.border = thin_border
            if row_idx == 1:
              cell.font = header_font
              cell.fill = header_fill
              cell.alignment = Alignment(
                  horizontal="center", vertical="center", wrap_text=True
              )
            else:
              cell.font = font_size_14
              cell.fill = light_gray_fill if row_idx % 2 == 0 else white_fill
              cell.alignment = Alignment(horizontal="right", vertical="center")

        ws.row_dimensions.height = 32
        for r in range(2, ws.max_row + 1):
          ws.row_dimensions[r].height = 26

        for col in ws.columns:
          max_len = max(len(str(cell.value or "")) for cell in col)
          col_letter = get_column_letter(col[0].column)
          ws.column_dimensions[col_letter].width = max(max_len + 6, 16)

      buffer_kpi.seek(0)

      st.download_button(
          label="📥 تحميل تقرير KPI النهائي (Excel منسق)",
          data=buffer_kpi,
          file_name="KPI_Report_Formatted.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      )

    except Exception as err:
      st.error(f"⚠️ خطأ أثناء معالجة الملف: {err}")
