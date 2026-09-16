import pandas as pd
import streamlit as st

# إعدادات الصفحة
st.set_page_config(
    page_title="نظام إدارة المحفظة المالية الكبرى - ASIA PAY", layout="wide"
)

# --- لوحة التحكم في الأعلى ---
st.markdown(
    "<h2 style='text-align: center; color: #1E3A8A;'>💰 نظام إدارة المحفظة"
    " المالية - ASIA PAY</h2>",
    unsafe_allow_html=True,
)

# استخدام الـ Tabs العلوية للتنقل السلس والسريع
app_mode = st.tabs(
    [
        "💳 محفظة ASIA PAY",
        "📊 الجرد الكلي ومقارنة الشهور",
        "⭐ نسب الأداء والنقاط",
    ]
)

# تحديد اسم ملف البيانات المحلي للمحفظة
DATA_FILE = "wallet_data_v4.csv"

# --- الحفاظ على حالة الجرد الكلي في الذاكرة ---
if "pivot_result" not in st.session_state:
  st.session_state["pivot_result"] = None
if "combined_df" not in st.session_state:
  st.session_state["combined_df"] = None


# دالة تحميل البيانات بأمان للمحفظة
def load_data():
  try:
    df = pd.read_csv(DATA_FILE)
    expected_columns = [
        "التاريخ",
        "نوع العملية",
        "المبلغ",
        "التفاصيل / الجهة / السبب",
        "طريقة الدفع",
        "حالة الديون",
        "الباقي في المحفظة",
    ]
    for col in expected_columns:
      if col not in df.columns:
        if col == "طريقة الدفع":
          df[col] = "كاش"
        elif col == "حالة الديون":
          df[col] = "لا توجد"
        else:
          df[col] = []
    return df
  except Exception:
    return pd.DataFrame(
        columns=[
            "التاريخ",
            "نوع العملية",
            "المبلغ",
            "التفاصيل / الجهة / السبب",
            "طريقة الدفع",
            "حالة الديون",
            "الباقي في المحفظة",
        ]
    )


# ====================================================
# القسم الأول: محفظة ASIA PAY (مع كافة الخصائص المسترجعة)
# ====================================================
with app_mode[0]:
  st.markdown("### 💼 محفظة ASIA PAY")
  st.markdown("---")

  df = load_data()

  total_deposit = (
      df[df["نوع العملية"] == "إيداع للمحفظة"]["المبلغ"].sum()
      if not df.empty and "نوع العملية" in df.columns
      else 0.0
  )

  col1, col2, col3 = st.columns(3)
  with col1:
    st.metric(
        label="الرصيد (الفعلي) الحالي في المحفظة",
        value=f"{df['الباقي في المحفظة'].iloc[-1] if not df.empty else 0:,.2f} د.ع",
    )
  with col2:
    st.metric(
        label="إجمالي مبالغ الإيداعات فقط", value=f"{total_deposit:,.2f} د.ع"
    )
  with col3:
    st.metric(
        label="إجمالي عدد الحركات المسجلة",
        value=str(len(df)) if not df.empty else "0",
    )

  st.markdown("---")

  c1, c2, c3 = st.columns(3)
  with c1:
    st.subheader("📥 إيداع للمحفظة")
    with st.form("deposit_form", clear_on_submit=True):
      deposit_amount = st.number_input(
          "المبلغ",
          value=None,
          min_value=0.0,
          step=1000.0,
          format="%.2f",
          key="dep_amt",
      )
      deposit_reason = st.text_input("سبب الإيداع / اسم المودع", key="dep_res")
      submit_deposit = st.form_submit_button("حفظ الإيداع")
      if submit_deposit:
        if deposit_amount is not None and deposit_amount > 0:
          current_bal = (
              df["الباقي في المحفظة"].iloc[-1]
              if (not df.empty and "الباقي في المحفظة" in df.columns)
              else 0.0
          )
          new_bal = current_bal + deposit_amount
          new_row = pd.DataFrame({
              "التاريخ": [str(pd.Timestamp.now())],
              "نوع العملية": ["إيداع للمحفظة"],
              "المبلغ": [deposit_amount],
              "التفاصيل / الجهة / السبب": [deposit_reason],
              "طريقة الدفع": ["إيداع"],
              "حالة الديون": ["لا توجد"],
              "الباقي في المحفظة": [new_bal],
          })
          df = pd.concat([df, new_row], ignore_index=True)
          df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
          st.success("تم حفظ الإيداع وتحديث الرصيد بنجاح!")
          st.rerun()
        else:
          st.warning("يرجى إدخال مبلغ صحيح.")

  with c2:
    st.subheader("📤 سحب كاش / مديونية")
    with st.form("withdraw_form", clear_on_submit=True):
      withdraw_amount = st.number_input(
          "المبلغ",
          value=None,
          min_value=0.0,
          step=1000.0,
          format="%.2f",
          key="wit_amt",
      )
      withdraw_reason = st.text_input(
          "اسم المكاتب / السحب منه / المسؤول", key="wit_res"
      )
      payment_method = st.selectbox(
          "طريقة الدفع / الحالة", ["كاش", "ماستر كارد", "مديونية (دين)"]
      )
      submit_withdraw = st.form_submit_button("حفظ السحب")
      if submit_withdraw:
        if withdraw_amount is not None and withdraw_amount > 0:
          current_bal = (
              df["الباقي في المحفظة"].iloc[-1]
              if (not df.empty and "الباقي في المحفظة" in df.columns)
              else 0.0
          )
          new_bal = current_bal - withdraw_amount
          debt_status = (
              "غير مسدد (مديونية)"
              if payment_method == "مديونية (دين)"
              else "مكتمل"
          )
          new_row = pd.DataFrame({
              "التاريخ": [str(pd.Timestamp.now())],
              "نوع العملية": ["سحب كاش"],
              "المبلغ": [withdraw_amount],
              "التفاصيل / الجهة / السبب": [withdraw_reason],
              "طريقة الدفع": [payment_method],
              "حالة الديون": [debt_status],
              "الباقي في المحفظة": [new_bal],
          })
          df = pd.concat([df, new_row], ignore_index=True)
          df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
          st.success("تم حفظ السحب وتحديث الرصيد بنجاح!")
          st.rerun()
        else:
          st.warning("يرجى إدخال مبلغ صحيح.")

  with c3:
    st.subheader("🔄 استرجاع مبالغ للمحفظة")
    with st.form("return_form", clear_on_submit=True):
      return_amount = st.number_input(
          "المبلغ الراجع",
          value=None,
          min_value=0.0,
          step=1000.0,
          format="%.2f",
          key="ret_amt",
      )
      return_reason = st.text_input("سبب الاسترجاع / من الجهة", key="ret_res")
      submit_return = st.form_submit_button("إلغاء واسترجاع للمحفظة")
      if submit_return:
        if return_amount is not None and return_amount > 0:
          current_bal = (
              df["الباقي في المحفظة"].iloc[-1]
              if (not df.empty and "الباقي في المحفظة" in df.columns)
              else 0.0
          )
          new_bal = current_bal + return_amount
          new_row = pd.DataFrame({
              "التاريخ": [str(pd.Timestamp.now())],
              "نوع العملية": ["استرجاع للمحفظة"],
              "المبلغ": [return_amount],
              "التفاصيل / الجهة / السبب": [return_reason],
              "طريقة الدفع": ["استرجاع"],
              "حالة الديون": ["لا توجد"],
              "الباقي في المحفظة": [new_bal],
          })
          df = pd.concat([df, new_row], ignore_index=True)
          df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
          st.success("تم استرجاع المبلغ وإضافته للمحفظة بنجاح!")
          st.rerun()
        else:
          st.warning("يرجى إدخال مبلغ صحيح.")

  st.markdown("---")
  st.subheader("📋 السجل التفصيلي للعمليات")
  if not df.empty:
    st.dataframe(df, use_container_width=True)

    # ميزة تعديل أو حذف عملية سابقة
    with st.expander("✏️ تعديل أو حذف عملية سابقة من السجل"):
      row_indices = df.index.tolist()
      selected_row_idx = st.selectbox(
          "اختر رقم السجل (Index) للتعديل أو الحذف:", row_indices
      )

      if selected_row_idx is not None:
        current_row = df.loc[selected_row_idx]

        with st.form("edit_row_form"):
          st.write(
              f"تعديل السجل رقم: {selected_row_idx} | التاريخ:"
              f" {current_row['التاريخ']}"
          )

          new_edit_amount = st.number_input(
              "تعديل المبلغ",
              value=float(current_row["المبلغ"]),
              step=1000.0,
              format="%.2f",
          )
          new_edit_reason = st.text_input(
              "تعديل التفاصيل / الجهة / السبب",
              value=str(current_row["التفاصيل / الجهة / السبب"]),
          )

          col_e1, col_e2 = st.columns(2)
          submit_edit = col_e1.form_submit_button("💾 حفظ التعديلات")
          submit_delete = col_e2.form_submit_button(
              "🗑️ حذف هذا السجل نهائياً"
          )

          if submit_edit:
            df.loc[selected_row_idx, "المبلغ"] = new_edit_amount
            df.loc[selected_row_idx, "التفاصيل / الجهة / السبب"] = (
                new_edit_reason
            )

            running_bal = 0.0
            for i in range(len(df)):
              op_type = df.loc[i, "نوع العملية"]
              op_amt = float(df.loc[i, "المبلغ"])
              if op_type in ["إيداع للمحفظة", "استرجاع للمحفظة"]:
                running_bal += op_amt
              else:
                running_bal -= op_amt
              df.loc[i, "الباقي في المحفظة"] = running_bal

            df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
            st.success("تم تحديث السجل بنجاح!")
            st.rerun()

          if submit_delete:
            df = df.drop(selected_row_idx).reset_index(drop=True)
            running_bal = 0.0
            for i in range(len(df)):
              op_type = df.loc[i, "نوع العملية"]
              op_amt = float(df.loc[i, "المبلغ"])
              if op_type in ["إيداع للمحفظة", "استرجاع للمحفظة"]:
                running_bal += op_amt
              else:
                running_bal -= op_amt
              df.loc[i, "الباقي في المحفظة"] = running_bal

            df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
            st.success("تم حذف السجل بنجاح!")
            st.rerun()
  else:
    st.info("لا توجد عمليات مسجلة حتى الآن.")

  # قسم جرد الحسابات والإحصائيات الشاملة
  st.markdown("---")
  st.subheader("📊 جرد الحسابات والإحصائيات الشاملة")
  if not df.empty:
    total_withdrawn = df[df["نوع العملية"] == "سحب كاش"]["المبلغ"].sum()
    total_deposited_sum = df[df["نوع العملية"] == "إيداع للمحفظة"][
        "المبلغ"
    ].sum()
    total_returned = df[df["نوع العملية"] == "استرجاع للمحفظة"]["المبلغ"].sum()
    current_remaining = df["الباقي في المحفظة"].iloc[-1]

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
      st.metric("إجمالي السحوبات", f"{total_withdrawn:,.2f} د.ع")
    with col_s2:
      st.metric("إجمالي الإيداعات", f"{total_deposited_sum:,.2f} د.ع")
    with col_s3:
      st.metric("إجمالي المبالغ المسترجعة", f"{total_returned:,.2f} د.ع")
    with col_s4:
      st.metric("صافي رصيد المحفظة النهائي", f"{current_remaining:,.2f} د.ع")

  # قسم قائمة الأشخاص والجهات المديونة
  st.markdown("---")
  st.subheader("📋 قائمة الأشخاص والجهات المديونة (غير المسددة)")
  if "حالة الديون" in df.columns:
    debts_df = df[df["حالة الديون"] == "غير مسدد (مديونية)"]

    if not debts_df.empty:
      st.warning(f"تنبيه: لديك {len(debts_df)} مديونيات غير مسددة حالياً.")

      debt_options = []
      for idx, row in debts_df.iterrows():
        debt_options.append(
            f"رقم السجل ({idx}) - الجهة/الشخص: {row['التفاصيل / الجهة / السبب']}"
            f" - المبلغ: {row['المبلغ']} د.ع"
        )

      selected_debt = st.selectbox("اختر المديونية لتسديدها:", debt_options)

      if st.button("✅ تم التسديد (تحديث وإزالة من المديونية)"):
        real_idx = int(
            selected_debt.split("رقم السجل (")[1].split(")")[0]
        )
        df.loc[real_idx, "حالة الديون"] = "تم التسديد"
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
        st.success("تم تسديد المديونية وتحديث حالتها بنجاح!")
        st.rerun()
    else:
      st.info("ممتاز! لا توجد أي مديونيات معلقة حالياً، جميع الحسابات خالصة 🎉.")

# ====================================================
# القسم الثاني: الجرد الكلي ومقارنة الشهور
# ====================================================
with app_mode[1]:
  st.markdown("### 📊 الجرد الكلي ومقارنة أداء المكاتب بين شهرين")
  st.write(
      "قم برفع ملف الشهر الأول والملف الثاني المقارن أدناه. ستبقى النتائج"
      " محفوظة بالكامل."
  )

  col_u1, col_u2 = st.columns(2)
  with col_u1:
    uploaded_file_8 = st.file_uploader(
        "اختر ملف الشهر الأول (Excel)", type=["xlsx", "xls"], key="file8"
    )
  with col_u2:
    uploaded_file_9 = st.file_uploader(
        "اختر ملف الشهر الثاني (Excel)", type=["xlsx", "xls"], key="file9"
    )

  if uploaded_file_8 is not None and uploaded_file_9 is not None:
    try:
      df8 = pd.read_excel(uploaded_file_8)
      df9 = pd.read_excel(uploaded_file_9)

      df8["Month"] = "Month_First"
      df9["Month"] = "Month_Second"

      combined_df = pd.concat([df8, df9], ignore_index=True)


      def clean_amount(val):
        if pd.isna(val):
          return 0.0
        val_str = str(val).replace(",", "").strip()
        try:
          return float(val_str)
        except:
          return 0.0


      combined_df["Cleaned_Amount"] = combined_df["Amount"].apply(clean_amount)

      translation_dict = {
          (
              "Agency Commission Roll Up from Independent Store to Head Office"
          ): "ترحيل عمولات الوكالة من المتاجر المستقلة إلى الإدارة الرئيسية",
          "Auto Claw Back": "استرجاع تلقائي للأموال",
          "Commission Payment for Head Office": "دفع العمولات للإدارة الرئيسية",
          "Commission Payment for Independent Stores": "دفع العمولات للمتاجر المستقلة",
          "Commission Roll Down for Independent Store": (
              "تنزيل العمولات للمتاجر المستقلة"
          ),
          "Customer Buy Goods Fee from Merchant": "أجور شراء بضائع من التاجر",
          "Customer Deposit at Agent": "إيداع نقدي للزبون لدى الوكيل",
          "Customer Withdraw at Agent": "سحب نقدي للزبون لدى الوكيل",
          "Organization Buy Airtime": "شراء رصيد / تعبئة من المؤسسة",
          "Organization Buy Electronic Vouchers": "شراء قسائم إلكترونية من المؤسسة",
          "Organization Deposit of Funds": "إيداع أموال للمؤسسة",
          (
              "Organization Inter Account Transfer - ORG to Agent"
          ): "تحويل بين حساب المؤسسة وحساب الوكيل",
          (
              "Organization Intra Account Transfer - Child to Child"
          ): "تحويل داخلي بين الفروع",
      }

      reason_col = (
          "Reason Type"
          if "Reason Type" in combined_df.columns
          else combined_df.columns[2]
      )
      combined_df["Arabic Translation"] = combined_df[reason_col].apply(
          lambda x: translation_dict.get(x, x)
      )

      pivot_result = combined_df.pivot_table(
          index=["Short Code", "Arabic Name", reason_col, "Arabic Translation"],
          columns="Month",
          values="Cleaned_Amount",
          aggfunc="sum",
          fill_value=0,
      ).reset_index()

      st.session_state["pivot_result"] = pivot_result
      st.session_state["combined_df"] = combined_df

      st.success("✅ تمت معالجة وحفظ الجرد الكلي بنجاح!")

    except Exception as e:
      st.error(f"⚠️ حدث خطأ أثناء المعالجة: {e}")

  if st.session_state["pivot_result"] is not None:
    st.subheader("📋 جدول مقارنة الجرد المحفوظ")
    st.dataframe(st.session_state["pivot_result"], use_container_width=True)

    output_filename = "Final_Inventory_Comparison_Report.xlsx"
    st.session_state["pivot_result"].to_excel(output_filename, index=False)
    with open(output_filename, "rb") as f:
      st.download_button(
          label="📥 تحميل تقرير المقارنة (Excel)",
          data=f,
          file_name=output_filename,
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
      )
  else:
    st.info(
        "💡 يرجى رفع ملفات الشهرين في الأعلى لعرض وجرد البيانات، وستبقى محفوظة"
        " هنا."
    )

# ====================================================
# القسم الثالث: نسب الأداء والنقاط
# ====================================================
with app_mode[2]:
  st.markdown("### ⭐ نسب الأداء وتقييم النقاط للمكاتب")
  st.write(
      "هذا القسم يعتمد مباشرة على بيانات الجرد الكلي ومقارنة الشهور للمكاتب"
      " (`Short Code` و `Arabic Name`)."
  )

  if (
      st.session_state["combined_df"] is not None
      and not st.session_state["combined_df"].empty
  ):
    df_combined = st.session_state["combined_df"]

    if "Short Code" in df_combined.columns and "Arabic Name" in df_combined.columns:
      perf_summary = (
          df_combined.groupby(["Short Code", "Arabic Name"])
          .agg(
              إجمالي_العمليات=("Cleaned_Amount", "count"),
              مجموع_المبالغ=("Cleaned_Amount", "sum"),
          )
          .reset_index()
      )


      def calc_score(row):
        amt = row["مجموع_المبالغ"]
        if amt > 5000000:
          return "ممتاز (95%)", int(amt / 10000)
        elif amt > 2000000:
          return "جيد جداً (85%)", int(amt / 10000)
        elif amt > 500000:
          return "جيد (75%)", int(amt / 10000)
        else:
          return "مقبول (60%)", int(amt / 10000)


      perf_summary[["نسبة الأداء", "النقاط المكتسبة"]] = perf_summary.apply(
          calc_score, axis=1, result_type="expand"
      )

      st.success("✅ تم احتساب نسب الأداء والنقاط تلقائياً من بيانات الجرد!")
      st.dataframe(perf_summary, use_container_width=True)
    else:
      st.warning(
          "⚠️ الأعمدة المطلوبة للمكاتب (Short Code / Arabic Name) غير متطابقة"
          " في الملفات المرفوعة."
      )
  else:
    st.info(
        "📌 لا توجد بيانات جرد حالياً. يرجى الذهاب إلى تبويب **(📊 الجرد الكلي"
        " ومقارنة الشهور)** ورفع الملفات أولاً، وسيقوم النظام هنا بحساب نسب"
        " الأداء والنقاط لكل مكتب تلقائياً!"
    )
