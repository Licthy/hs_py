import tkinter as tk
from tkinter import messagebox


def calc(sum_value, gender):
    sum_value1 = 11 - sum_value if gender == "男" else 4 + sum_value
    if sum_value1 > 9 and sum_value1 > 0:
        sum_value1 = calc(sum_value - 9, gender)
    elif sum_value1 < 0:
        sum_value1 = calc(sum_value - 9, gender)

    # 如果等于5，那么判定性别
    if sum_value1 == 5:
        sum_value1 = 2 if gender == "男" else 8

    return sum_value1


def calculate_e():
    """核心计算函数，按照规则计算最终结果，并打印/显示过程值"""
    # 获取输入的出生年份
    year_input = entry_year.get().strip()
    # 获取选中的性别
    gender = var_gender.get()

    # 输入验证：确保年份是四位数的数字
    try:
        birth_year = int(year_input)
        if not (1000 <= birth_year <= 9999):
            messagebox.showerror("输入错误", "请输入四位数的出生年份（如1994）！")
            return
    except ValueError:
        messagebox.showerror("输入错误", "年份必须是数字，请重新输入！")
        return

    # 步骤1：拆分年份各位数字求和得到A
    digits = [int(d) for d in str(birth_year)]
    sum_value = sum(digits)
    reply = calc(sum_value, gender)

    # ========== 2. 界面显示过程值（直观查看） ==========
    process_text = (
        f"男用11减，女用4加，5的时候男转2女转8\n"
        f"出生年份：{birth_year} 和：{sum_value}\n"
        f"性别：{gender}\n"
        f"结果：{reply}"
    )
    # 清空原有内容并插入新的过程值
    text_process.delete(1.0, tk.END)
    text_process.insert(tk.END, process_text)

    # 显示最终结果
    label_result.config(text=f"结果：{reply}")


# 创建主窗口
root = tk.Tk()
root.title("出生年份计算工具")
root.geometry("500x400")  # 扩大窗口以容纳过程显示区域

# 1. 出生年份输入区域
frame_year = tk.Frame(root)
frame_year.pack(pady=10)
label_year = tk.Label(frame_year, text="出生年份（四位数）：")
label_year.pack(side=tk.LEFT, padx=5)
entry_year = tk.Entry(frame_year, width=20)
entry_year.pack(side=tk.LEFT)

# 2. 性别选择区域
frame_gender = tk.Frame(root)
frame_gender.pack(pady=5)
var_gender = tk.StringVar(value="男")  # 默认选中男性
radio_male = tk.Radiobutton(frame_gender, text="男", variable=var_gender, value="男")
radio_male.pack(side=tk.LEFT, padx=10)
radio_female = tk.Radiobutton(frame_gender, text="女", variable=var_gender, value="女")
radio_female.pack(side=tk.LEFT, padx=10)

# 3. 计算按钮
btn_calculate = tk.Button(root, text="计算结果", command=calculate_e)
btn_calculate.pack(pady=10)

# 4. 过程显示区域（新增）
label_process = tk.Label(root, text="计算过程详情：")
label_process.pack(pady=5)
text_process = tk.Text(root, width=50, height=8)
text_process.pack(padx=10)

# 5. 最终结果显示区域
label_result = tk.Label(root, text="最终结果为：", font=("Arial", 12))
label_result.pack(pady=10)

# 启动主循环
root.mainloop()
