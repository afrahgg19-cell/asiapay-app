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
    "📈 KPI والدمج الشامل",
])

with tab1:
  st.info("التبويب الأول - محفظة ASIA PAY")

with tab2:
  st.info("التبويب الثاني - المقارنة بين شهرين")

with tab3:
  st.info("التبويب الثالث - نسبة الإنجاز")

with tab_kpi:
  st.markdown(
      "### 🔗 مطابقة ودمج بيانات المحفظة والحركات حسب الشورت كود"
  )
  st.write(
      "ارفع **ملف الإكسل الرئيسي** (يحتوي على ورقة الحركات ورقة 'Wallet report')"
      " و**ملف المندوبين الاختياري**."
  )

  col_k1, col_k2 = st.columns(2)
  with col_k1:
    kpi_uploaded_file = st.file_uploader(
        "اختر ملف الإكسل الرئيسي", type=["xlsx", "xls"], key="kpi_main_full"
    )
  with col_k2:
    rep_uploaded_file = st.file_uploader(
        "اختر ملف المندوبين (اختياري)",
        type=["xlsx", "xls"],
        key="kpi_rep_full",
    )

  if kpi_uploaded_file is not None:
    try:
      excel_file_obj = pd.ExcelFile(kpi_uploaded_file)
      sheet_names = excel_file_obj.sheet_names
      st.info(f"📁 الأوراق المكتشفة داخل الملف: {sheet_names}")

      # قراءة الورقة الأولى للحركات (الشورت كود E والاسم بالعربي F)
      kpi_df = pd.read_excel(kpi_uploaded_file, sheet_name=0)

      # البحث عن ورقة Wallet report
      wallet_sheet_name = None
      for s in sheet_names:
        if "wallet" in s.lower():
          wallet_sheet_name = s
          break
      if not wallet_sheet_name and len(sheet_names) > 1:
        wallet_sheet_name = sheet_names

      wallet_data_map = {}
      if wallet_sheet_name:
        w_df = pd.read_excel(kpi_uploaded_file, sheet_name=wallet_sheet_name)
        st.caption(
            f"✅ يتم قراءة بيانات المحفظة من الورقة: '{wallet_sheet_name}'"
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

        # البحث عن رقم المحفظة / الحساب
        wallet_num_col = next(
            (
                c
                for c in w_df.columns
                if "number" in str(c).lower()
                or ("account" in str(c).lower() and c != h_col_w)
            ),
            None,
        )
        if not wallet_num_col and len(w_df.columns) > 1:
          wallet_num_col = w_df.columns

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
          filtered_w["wallet_num"] = (
              filtered_w[wallet_num_col].astype(str).str.strip()
              if wallet_num_col is not None
              else ""
          )
          filtered_w["acc_type"] = (
              filtered_w[h_col_w].astype(str).str.strip()
          )

          for _, wrow in filtered_w.iterrows():
            k_key = wrow["key_clean"]
            if k_key and k_key != "NAN":
              wallet_data_map[k_key] = {
                  "رقم المحفظة": wrow.get("wallet_num", ""),
                  "حالة/نوع المحفظة": wrow.get("acc_type", ""),
                  "رصيد المحفظة (التل)": wrow.get("cleaned_R", 0.0),
              }
          st.success("✅ تمت قراءة وتطابق بيانات ورقة المحفظة بنجاح!")

      # تجهيز أعمدة الحركات الرئيسية (الشورت كود E والاسم بالعربي F)
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
      work_kpi["T_num"] = pd.to_numeric(
          raw_t_series.str.replace(",", "", regex=False)
          .str.replace(" ", "", regex=False)
          .str.replace("$", "", regex=False),
          errors="coerce",
      ).fillna(0.0)

      # قراءة ملف المندوبين
      has_rep_file = rep_uploaded_file is not None
      rep_map_dict = {}
      if has_rep_file:
        try:
          rep_df = pd.read_excel(rep_uploaded_file)
          c_idx = rep_df.columns
          n_idx = rep_df.columns if len(rep_df.columns) > 1 else c_idx
          for _, rrow in rep_df.iterrows():
            c_val = str(rrow[c_idx]).strip().upper()
            n_val = str(rrow[n_idx]).strip()
            if c_val and c_val != "NAN":
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

      merged_rows_list = []
      for (e_v, f_v), grp in work_kpi.groupby(
          ["E_clean", "F_clean"], dropna=False
      ):
        g_str_key = str(e_v).strip().upper()
        w_info = wallet_data_map.get(
            g_str_key,
            {
                "رقم المحفظة": "غير متوفر",
                "حالة/نوع المحفظة": "غير متوفر",
                "رصيد المحفظة (التل)": 0.0,
            },
        )
        emp_name = (
            rep_map_dict.get(g_str_key, "غير محدد")
            if has_rep_file
            else "غير محدد"
        )

        wallet_val = w_info["رصيد المحفظة (التل)"]
        b2b_mask = grp["B_clean"].str.lower() == "business to business transfer"
        total_b2b_sum = grp.loc[b2b_mask, "T_num"].sum()

        row_item = {
            "Short Code (E)": e_v,
            "الاسم بالعربي (F)": f_v,
            "اسم الموظف": emp_name,
            "رقم المحفظة": w_info["رقم المحفظة"],
            "حالة/نوع المحفظة": w_info["حالة/نوع المحفظة"],
            "رصيد المحفظة (التل)": (
                f"{wallet_val:,.2f}"
                if isinstance(wallet_val, (int, float, np.number))
                else wallet_val
            ),
        }

        for op in target_ops:
          row_item[f"عدد ({op})"] = int(
              (grp["B_clean"].str.lower() == op.lower()).sum()
          )

        row_item["مجموع مبالغ B2B"] = (
            f"{int(total_b2b_sum):,}"
            if total_b2b_sum == int(total_b2b_sum)
            else f"{total_b2b_sum:,.2f}"
        )

        merged_rows_list.append(row_item)

      final_merged_table = pd.DataFrame(merged_rows_list)
      st.subheader("📋 الجدول المدمج والمطابق حسب الشورت كود")
      st.dataframe(final_merged_table, use_container_width=True)

      buffer_out = BytesIO()
      with pd.ExcelWriter(buffer_out, engine="openpyxl") as writer:
        final_merged_table.to_excel(
            writer, index=False, sheet_name="Merged_KPI_Wallet"
        )
        wb = writer.book
        ws = wb["Merged_KPI_Wallet"]

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

      buffer_out.seek(0)

      st.download_button(
          label="📥 تحميل التقرير المدمج نهائياً (Excel منسق خط 14 + حدود)",
          data=buffer_out,
          file_name="Merged_ShortCode_Wallet_Report.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      )

    except Exception as err:
      st.error(f"⚠️ خطأ أثناء معالجة الدمج: {err}")
