import pandas as pd

# ضع مسار ملف الاكسل هنا
excel_path = 'your_file.xlsx'

# 1. قراءة الورقتين (الورقة الأولى index=0، والورقة الثانية index=1)
df_sheet1 = pd.read_excel(excel_path, sheet_name=0)
df_sheet2 = pd.read_excel(excel_path, sheet_name=1)

# 2. تحديد الأعمدة بدقة بناءً على طلبك (الشورت كود في E بالورقة 2، والمبالغ كنصوص تحول لأرقام)
# عمود الشورت كود في الورقة الأولى غالباً أول عمود أو عمود 'Short Code (G)'
col_short_s1 = (
    'Short Code (G)'
    if 'Short Code (G)' in df_sheet1.columns
    else df_sheet1.columns[0]
)
# عمود الشورت كود في الورقة الثانية (عمود E أو index 4 غالباً، أو البحث عن عمود يمتلك code)
col_short_s2 = (
    'shortCode'
    if 'shortCode' in df_sheet2.columns
    else [
        c
        for c in df_sheet2.columns
        if 'code' in str(c).lower() or 'short' in str(c).lower()
    ][0]
)

# عمود المبالغ (عمود R أو 'balance' أو أي عمود تريده - هنا سنأخذ عمود balance أو R الفعلي)
# إذا كان عمود R حرفي أو اسمه مشابه، نتحقق منه:
target_amount_col = None
for col in df_sheet2.columns:
  if str(col).strip().upper() == 'R' or 'bal' in str(col).lower():
    target_amount_col = col
    break
if not target_amount_col:
  target_amount_col = (
      df_sheet2.columns[8] if len(df_sheet2.columns) > 8 else df_sheet2.columns[-1]
  )  # افتراضي عمود متقدم أو الأخير

print(f'تم اختيار عمود الشورت كود 1: {col_short_s1}')
print(f'تم اختيار عمود الشورت كود 2: {col_short_s2}')
print(f'تم اختيار عمود المبالغ/الرصيد: {target_amount_col}')


# 3. تنظيف وتوحيد الشورت كود (إزالة المسافات، تحويل لأحرف كبيرة)
df_sheet1['clean_code_s1'] = (
    df_sheet1[col_short_s1].astype(str).str.strip().str.upper()
)
df_sheet2['clean_code_s2'] = (
    df_sheet2[col_short_s2].astype(str).str.strip().str.upper()
)


# 4. تنظيف وتحويل عمود المبالغ (نصوص فواصل إلى أرقام)
def convert_to_number(val):
  if pd.isna(val):
    return 0.0
  s = (
      str(val)
      .replace(',', '')
      .replace(' ', '')
      .replace('$', '')
      .replace('"', '')
      .strip()
  )
  try:
    return float(s)
  except:
    return 0.0


df_sheet2['numeric_balance'] = df_sheet2[target_amount_col].apply(
    convert_to_number
)

# طباعة عينة للتحقق من أن القيم تحولت لأرقام وليست صفراً
print('عينة من المبالغ المحولة في الورقة الثانية:')
print(
    df_sheet2[[col_short_s2, target_amount_col, 'numeric_balance']].head(10)
)

# 5. تجميع الرصيد لكل شورت كود في الورقة الثانية (في حال تكرار الشورت كود)
aggregated_df = (
    df_sheet2.groupby('clean_code_s2')['numeric_balance'].sum().reset_index()
)
aggregated_df.rename(columns={'numeric_balance': 'رصيد المحفظة'}, inplace=True)

# 6. الدمج مع الورقة الأولى (Left Join)
df_merged = pd.merge(
    df_sheet1,
    aggregated_df,
    left_on='clean_code_s1',
    right_on='clean_code_s2',
    how='left',
)

# تعبئة القيم الفارغة بـ 0
df_merged['رصيد المحفظة'] = df_merged['رصيد المحفظة'].fillna(0.0)

# حذف الأعمدة المؤقتة لتنظيف الجدول
df_merged.drop(
    columns=['clean_code_s1', 'clean_code_s2'], inplace=True, errors='ignore'
)

# 7. حفظ التقرير النهائي في ملف Excel جديد
output_file = 'final_fixed_report.xlsx'
df_merged.to_excel(output_file, index=False)

print(f'\nتم بنجاح! تم حفظ الملف باسم: {output_file}')
print('عينة نهائية من الجدول بعد إضافته:')
print(df_merged.head(15))
