import streamlit as st
import pandas as pd
import numpy as np

# إعدادات الصفحة
st.set_page_config(
    page_title="نظام الإدارة المتبوع - استعلام وتاركت",
    page_icon="📊",
    layout="wide"
)

# تهيئة بيانات تجريبية أو جلسة تخزين إذا لم تكن موجودة
if 'df_deposits' not in st.session_state:
    st.session_state.df_deposits = pd.DataFrame({
        'التاريخ': pd.to_datetime(['2026-09-01', '2026-09-10', '2026-09-20']),
        'البيان': ['إيداع أول', 'إيداع ثاني', 'إيداع ثالث'],
        'المبلغ': [500000, 750000, 300000]
    })

if 'target_total' not in st.session_state:
    st.session_state.target_total = 3000000  # التاركت الافتراضي الكلي للإيداعات

st.title("🚀 نظام الإدارة الشامل (Streamlit)")

# تقسيم التطبيق إلى تبويبات
tab1, tab2, tab3 = st.tabs(["📊 التبويب الأول: الإيداعات والتاركت", "📦 التبويب الثاني: البيانات/المخزون", "⚙️ التبويب الثالث: الإعدادات"])

# ==========================================
# 📊 التبويب الأول: الإيداعات وتاركت الكلي
# ==========================================
with tab1:
    st.header("إدارة الإيداعات ومتابعة التاركت")
    
    # قسم لإضافة إيداع جديد (اختعاري لتحديث البيانات)
    with st.expander("➕ إضافة إيداع جديد"):
        with st.form("add_dep_form"):
            col_a, col_b = st.columns(2)
            new_date = col_a.date_input("التاريخ", value=pd.Timestamp.today())
            new_desc = col_text = col_b.text_input("البيان / التفصيل", value="إيداع جديد")
            new_amount = st.number_input("مبلغ الإيداع", min_value=0.0, step=10000.0)
            submitted = st.form_submit_button("إضافة للإيداعات")
            if submitted:
                new_row = pd.DataFrame({'التاريخ': [pd.to_datetime(new_date)], 'البيان': [new_desc], 'المبلغ': [new_amount]})
                st.session_state.df_deposits = pd.concat([st.session_state.df_deposits, new_row], ignore_index=True)
                st.success("تمت إضافة الإيداع بنجاح!")
                st.rerun()

    # عرض جدول الإيداعات الحالية
    st.subheader("سجل الإيداعات الحالية")
    st.dataframe(st.session_state.df_deposits, use_container_width=True)

    # حساب إجمالي إيداعاتك الفعلية من الداتا
    my_deposits_total = st.session_state.df_deposits['المبلغ'].sum()
    st.metric(label="إجمالي إيداعاتك الواصلة فعلياً", value=f"{my_deposits_total:,.0f} د.ع")

    st.divider()

    # 🎯 إضافة حقل تاركت الإيداعات الكليه ليجوه (أسفل التبويب)
    st.markdown("### 🎯 مستهدف الإيداعات الكلية (Target)")
    target_deposits = st.number_input(
        "أدخل تاركت الإيداعات الكلية المطلوب:",
        min_value=1.0,
        value=float(st.session_state.target_total),
        step=50000.0,
        format="%.0f"
    )
    # تحديث القيمة في الـ session
    st.session_state.target_total = target_deposits

    # الحسابات المطلوبة (نقص الإيداعات مالتي من الإيداعات الكلية + النسبة المئوية)
    remaining_or_diff = target_deposits - my_deposits_total
    percentage = (my_deposits_total / target_deposits) * 100 if target_deposits > 0 else 0

    # عرض النتائج بشكل جميل وواضح
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="التاركت الكلي", value=f"{target_deposits:,.0f}")
    with col2:
        if remaining_or_diff >= 0:
            st.metric(label="المبلغ المتبقي للوصول للتاركت", value=f"{remaining_or_diff:,.0f}", delta=f"-{remaining_or_diff:,.0f}", delta_color="off")
        else:
            st.metric(label="تجاوز التاركت بزيادة", value=f"{abs(remaining_or_diff):,.0f}", delta=f"+{abs(remaining_or_diff):,.0f}", delta_color="normal")
    with col3:
        st.metric(label="نسبة الإنجاز واصلين", value=f"{percentage:.2f} %")

    # شريط تقدم (Progress Bar) لمزيد من التوضيح البصري
    progress_val = min(percentage / 100.0, 1.0)
    st.progress(progress_val)
    
    if percentage >= 100:
        st.success(f"🎉 مبروك! لقد تجاوزتم أو أتممتم تاركت الإيداعات الكلية بنجاح (واصلين {percentage:.2f}%).")
    else:
        st.info(f"📌 نسبتنا الحالية واصلة إلى **{percentage:.2f}%** من إجمالي التاركت المطلوب (متبقي {remaining_or_diff:,.0f}).")

# ==========================================
# 📦 التبويب الثاني: البيانات / إضافات أخرى
# ==========================================
with tab2:
    st.header("التبويب الثاني - بيانات عامة أو مخزون")
    st.write("هنا يمكنك وضع أي جداول أو تحليلات إضافية خاصة بك.")
    sample_df = pd.DataFrame(np.random.randn(5, 3), columns=['العمود A', 'العمود B', 'العمود C'])
    st.dataframe(sample_df)

# ==========================================
# ⚙️ التبويب الثالث: الإعدادات
# ==========================================
with tab3:
    st.header("إعدادات النظام")
    if st.button("تصفير بيانات الإيداعات التجريبية"):
        st.session_state.df_deposits = pd.DataFrame(columns=['التاريخ', 'البيان', 'المبلغ'])
        st.rerun()
    st.write("تم حفظ الإعدادات بنجاح.")
