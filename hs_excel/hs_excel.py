import pandas as pd

# 读取 Excel 文件
df = pd.read_excel('E:/Code/git/hs_py/hs_excel/四川.xls', sheet_name=0)  # sheet_name=0 表示第一个表

# 查看前几行数据
print(df.head())

# 单独取某一列，比如姓名
print(df['姓名'])

# 遍历每一行，取出字段
for index, row in df.iterrows():
    name = row['姓名']
    id_card = row['身份证']
    chinese = row['语文']
    math = row['数学']
    print(f"{name} | {id_card}  | 语文:{chinese} | 数学:{math}")
