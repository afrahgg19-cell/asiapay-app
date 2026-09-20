import pandas as pd
import streamlit as st

# إعدادات الصفحة
st.set_page_config(
    page_title="نظام إدارة المحفظة المالية الكبرى - ASIA PAY", layout="wide"
)

st.title("💼 ASIA PAY محفظة")
st.markdown("---")

# تحديد اسم ملف البيانات
DATA_FILE = "wallet_data_v4.csv"


# دالة تحميل البيانات بأمان
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


# تحميل البيانات الحالية
df = load_data()

# حساب إجمالي الإيداعات
total_deposit = (
    df[df["نوع العملية"] == "إيداع للمحفظة"]["المبلغ"].sum()
    if not df.empty and "نوع العملية" in df.columns
    else 0.0
)

# لوحة المؤشرات العلوية
col1, col2, col3 = st.columns(3)
with col1:
  st.metric(
      label="الرصيد (الفعلي) الحالي في المحفظة",
      value=f"{df['الباقي في المحفظة'].iloc[-1] if not df.empty else 0:,.2f} د.ع",
  )
with col2:
  st.metric(label="إجمالي مبالغ الإيداعات فقط", value=f"{total_deposit:,.2f} د.ع")
with col3:
  st.metric(
      label="إجمالي عدد الحركات المسجلة", value=str(len(df)) if not df.empty else "0"
  )

st.markdown("---")

# أقسام العمليات (إيداع، سحب، واسترجاع مبالغ للمحفظة) - بدون أصفار افتراضية
c1, c2, c3 = st.columns(3)

with c1:
  st.subheader("📥 إيداع للمحفظة")
  with st.form("deposit_form", clear_on_submit=True):
    deposit_amount = st.number_input(
        "المبلغ", value=None, min_value=0.0, step=1000.0, format="%.2f", key="dep_amt"
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
        "المبلغ", value=None, min_value=0.0, step=1000.0, format="%.2f", key="wit_amt"
    )
    withdraw_reason = st.text_input("اسم المكاتب / السحب منه / المسؤول", key="wit_res")
    
    payment_method = st.selectbox(
        "طريقة الدفع / الحالة",
        ["كاش", "ماستر كارد", "مديونية (دين)"]
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
        debt_status = "غير مسدد (مديونية)" if payment_method == "مديونية (دين)" else "مكتمل"

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
        "المبلغ الراجع", value=None, min_value=0.0, step=1000.0, format="%.2f", key="ret_amt"
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

# عرض الجدول التفصيلي للعمليات
st.markdown("---")
st.subheader("📋 السجل التفصيلي للعمليات")
if not df.empty:
  st.dataframe(df, use_container_width=True)
  
  with st.expander("✏️ تعديل أو حذف عملية سابقة من السجل"):
    row_indices = df.index.tolist()
    selected_row_idx = st.selectbox("اختر رقم السجل (Index) للتعديل أو الحذف:", row_indices)
    
    if selected_row_idx is not None:
      current_row = df.loc[selected_row_idx]
      
      with st.form("edit_row_form"):
        st.write(f"تعديل السجل رقم: {selected_row_idx} | التاريخ: {current_row['التاريخ']}")
        
        new_edit_amount = st.number_input("تعديل المبلغ", value=float(current_row['المبلغ']), step=1000.0, format="%.2f")
        new_edit_reason = st.text_input("تعديل التفاصيل / الجهة / السبب", value=str(current_row['التفاصيل / الجهة / السبب']))
        types_list = ["إيداع للمحفظة", "سحب كاش", "استرجاع للمحفظة"]
        default_idx = types_list.index(current_row['نوع العملية']) if current_row['نوع العملية'] in types_list else 0
        new_edit_type = st.selectbox("نوع العملية", types_list, index=default_idx)
        
        col_e1, col_e2 = st.columns(2)
        submit_edit = col_e1.form_submit_button("💾 حفظ التعديلات")
        submit_delete = col_e2.form_submit_button("🗑️ حذف هذا السجل نهائياً")
        
        if submit_edit:
          df.loc[selected_row_idx, 'المبلغ'] = new_edit_amount
          df.loc[selected_row_idx, 'التفاصيل / الجهة / السبب'] = new_edit_reason
          df.loc[selected_row_idx, 'نوع العملية'] = new_edit_type
          
          running_bal = 0.0
          for i in range(len(df)):
            op_type = df.loc[i, 'نوع العملية']
            op_amt = float(df.loc[i, 'المبلغ'])
            if op_type in ["إيداع للمحفظة", "استرجاع للمحفظة"]:
              running_bal += op_amt
            else:
              running_bal -= op_amt
            df.loc[i, 'الباقي في المحفظة'] = running_bal
            
          df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
          st.success("تم تحديث السجل وإعادة حساب أرصدة المحفظة بنجاح!")
          st.rerun()
          
        if submit_delete:
          df = df.drop(selected_row_idx).reset_index(drop=True)
          
          running_bal = 0.0
          for i in range(len(df)):
            op_type = df.loc[i, 'نوع العملية']
            op_amt = float(df.loc[i, 'المبلغ'])
            if op_type in ["إيداع للمحفظة", "استرجاع للمحفظة"]:
              running_bal += op_amt
            else:
              running_bal -= op_amt
            df.loc[i, 'الباقي في المحفظة'] = running_bal
            
          df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
          st.success("تم حذف السجل وإعادة ترتيب المحفظة بنجاح!")
          st.rerun()
else:
  st.info("لا توجد عمليات مسجلة حتى الآن.")

# الجرد والإحصائيات الشاملة في نهاية الصفحة
st.markdown("---")
st.subheader("📊 جرد الحسابات والإحصائيات الشاملة")

if not df.empty:
  total_withdrawn = df[df["نوع العملية"] == "سحب كاش"]["المبلغ"].sum()
  total_deposited_sum = df[df["نوع العملية"] == "إيداع للمحفظة"]["المبلغ"].sum()
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

# قسم الأشخاص المديونين في نهاية الصفحة
st.markdown("---")
st.subheader("📋 قائمة الأشخاص والجهات المديونة (غير المسددة)")

if "حالة الديون" in df.columns:
  debts_df = df[df["حالة الديون"] == "غير مسدد (مديونية)"]
  
  if not debts_df.empty:
    st.warning(f"تنبيه: لديك {len(debts_df)} مديونيات غير مسددة حالياً.")
    
    debt_options = []
    for idx, row in debts_df.iterrows():
      debt_options.append(f"رقم السجل ({idx}) - الجهة/الشخص: {row['التفاصيل / الجهة / السبب']} - المبلغ: {row['المبلغ']} د.ع")
      
    selected_debt = st.selectbox("اختر المديونية لتسديدها:", debt_options)
    
    if st.button("✅ تم التسديد (تحديث وإزالة من المديونية)"):
      real_idx = int(selected_debt.split("رقم السجل (").split(")")[0])
      df.loc[real_idx, "حالة الديون"] = "تم التسديد"
      df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
      st.success("تم تسديد المديونية وتحديث حالتها بنجاح!")
      st.rerun()
  else:
    st.info("ممتاز! لا توجد أي مديونيات معلقة حالياً، جميع الحسابات خالصة 🎉.")
