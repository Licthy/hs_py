bagua_mapping = {
    1: "坎1",
    2: "坤2",
    3: "震3",
    4: "巽4",
    6: "乾6",
    7: "兑7",
    8: "艮8",
    9: "离9",
}


def calc(sum_value, gender):
    """仅负责计算最终的数字结果，不打印，返回数字"""
    # 第一步：根据性别计算初始值
    if gender == "男":
        sum_value1 = 11 - sum_value
    else:
        sum_value1 = 4 + sum_value

    # 第二步：循环调整，确保结果在1-9之间（替代错误的递归）
    while sum_value1 > 9 or sum_value1 < 1:
        if sum_value1 > 9:
            sum_value1 -= 9  # 大于9则减9
        elif sum_value1 < 1:
            sum_value1 += 9  # 小于1则加9（原逻辑错误，此处修正）

    # 第三步：处理数字5的特殊规则
    if sum_value1 == 5:
        sum_value1 = 2 if gender == "男" else 8

    return sum_value1


def calc_year_sum(birth_year, gender):
    """拆分年份求和，调用calc计算最终值，并打印结果"""
    # 拆分年份各位数字并求和
    digits = [int(d) for d in str(birth_year)]
    sum_value = sum(digits)
    # 获取最终计算的数字
    final_num = calc(sum_value, gender)
    # 映射到卦象（无对应值则显示"输入无效！"）
    final_gua = bagua_mapping.get(final_num, "输入无效！")
    # 仅打印一次最终结果
    return final_gua


for year in range(2000, 2030):
    print(
        f"{year}男：{calc_year_sum(year, '男')}；{year}女：{calc_year_sum(year, '女')}"
    )
