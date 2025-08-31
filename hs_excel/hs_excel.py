import pandas as pd

# 读取 Excel 文件
df = pd.read_excel('C:/Users/Li/Desktop/证书审核.xlsx', sheet_name=0)  # sheet_name=0 表示第一个表
# # 查看前几行数据
# print(df.head())
# # 单独取某一列，比如姓名
# print(df['姓名'])
# 遍历每一行，取出字段
for index, row in df.iterrows():
    name = row['姓名']
    id_card = row['身份证']
    state = row['状态']
    city = row['地区']
    if state=="学习中":
        print(f"{name} | {id_card}  | 语文:{state} | 数学:{city}")
