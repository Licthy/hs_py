import os
import re
import tkinter as tk
from tkinter import messagebox, scrolledtext

# ===================== 核心代码生成函数 =====================
def ensure_dir_exists(dir_path):
    """确保目录存在，不存在则创建"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def generate_db_erl(DirPath, ModuleName, Desc):
    """生成 xxx_db.erl 文件（对应auto_db.erl）"""
    file_path = os.path.join(DirPath, f"{ModuleName}_db.erl")
    content = f"""%%%-------------------------------------------------------------------
%%% @author ljh,lvjihong@youkia.net
%%% @copyright (C) 2024, youkia,www.youkia.net
%%% @doc
%%%
%%% @end
%%%-------------------------------------------------------------------
-module({ModuleName}_db).

-description("{Desc}").
-author("lvjihong").

%%%=======================EXPORT=======================
-export([get_data/2, update/2]).

%%%=======================INCLUDE======================

%%%=======================DEFINE=======================

%%%=======================RECORD=======================

%%%=================EXPORTED FUNCTIONS=================
%% ----------------------------------------------------
%%{Desc}获取数据
%% ----------------------------------------------------
get_data(_Src, RoleUid)->
    ServerId = uid_lib:get_server(RoleUid),
    z_db_lib:get(z_db_lib:get_table('{ModuleName}', ServerId), RoleUid, []).

%% ----------------------------------------------------
%%更新数据
%% ----------------------------------------------------
update({{}}, [{{Index1,RoleData}}])->
    RoleData1 = RoleData,
    {{ok, ok, [{{Index1, RoleData1}}]}}.


%%%===================LOCAL FUNCTIONS==================
%% ----------------------------------------------------
%%
%% ----------------------------------------------------
"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return f"生成 {file_path} 成功"

def generate_db_cfg(DirPath, ModuleName, Desc):
    """生成 xxx_db.cfg 文件（对应auto_db_cfg.erl）"""
    Upper = ModuleName.upper()
    file_path = os.path.join(DirPath, f"{ModuleName}_db.cfg")
    content = f"""%%{Desc}
{{local, {Upper}, z_lib, to_atom, [GameProject, "/{ModuleName}"]}}.
{{template, _FILE_TABLE, {{{ModuleName}, {Upper}}}}}.
"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return f"生成 {file_path} 成功"

def generate_lib_erl(DirPath, ModuleName, Desc):
    """生成 xxx.erl 文件（对应auto_lib.erl）"""
    file_path = os.path.join(DirPath, f"{ModuleName}.erl")
    content = f"""%%%-------------------------------------------------------------------
%%% @author ljh,lvjihong@youkia.net
%%% @copyright (C) 2024, youkia,www.youkia.net
%%% @doc
%%%
%%% @end
%%%-------------------------------------------------------------------
-module({ModuleName}).

-description("{Desc}").
-author("lvjihong").

%%%=======================EXPORT=======================
-export([]).

%%%=======================INCLUDE======================

%%%=======================DEFINE=======================

%%%=======================RECORD=======================
-record({ModuleName}, {{

}}).
%%%=================EXPORTED FUNCTIONS=================
%% ----------------------------------------------------
%%
%% ----------------------------------------------------




%%%===================LOCAL FUNCTIONS==================
%% ----------------------------------------------------
%%
%% ----------------------------------------------------
"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return f"生成 {file_path} 成功"

def generate_pb_proto(DirPath, ModuleName, Desc):
    """生成 pb_xxx.proto 文件（对应auto_pb.erl）"""
    file_path = os.path.join(DirPath, f"pb_{ModuleName}.proto")
    content = f"""//功能:{Desc}
syntax = "proto3";
import "pb_pub.proto";


// 前端 获取数据
message cs_{ModuleName}_get_data {{
}}
// 服务器返回 获取数据
message sc_{ModuleName}_get_data {{
}}


// 前端 更新数据
message cs_{ModuleName}_update {{
}}
// 服务器返回 更新数据
message sc_{ModuleName}_update {{
}}
"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return f"生成 {file_path} 成功"

def generate_port_erl(DirPath, ModuleName, Desc):
    """生成 xxx_port.erl 文件（对应auto_port.erl）"""
    file_path = os.path.join(DirPath, f"{ModuleName}_port.erl")
    content = f"""%%%-------------------------------------------------------------------
%%% @author ljh,lvjihong@youkia.net
%%% @copyright (C) 2024, youkia,www.youkia.net
%%% @doc
%%%
%%% @end
%%%-------------------------------------------------------------------
-module({ModuleName}_port).

-description("{Desc}").
-author("lvjihong").

%%%=======================EXPORT=======================
-export([get_data/5]).

%%%=======================INCLUDE======================

%%%=======================DEFINE=======================

%%%=======================RECORD=======================

%%%=================EXPORTED FUNCTIONS=================
%% ----------------------------------------------------
%% {ModuleName}获取数据
%% ----------------------------------------------------
get_data(_, _Session, Attr, Info, _Pb) ->
    Src = z_lib:get_value(Info, src, ""),
    RoleUid = role_lib:get_uid(Attr),
    RoleData = {ModuleName}_db:get_data(Src, RoleUid),
    R = pb_{ModuleName}:init_sc_{ModuleName}_get_data(),
    {{ok, [], Info, R}}.
%% ----------------------------------------------------
%%
%% ----------------------------------------------------
update(_, _Session, Attr, Info, Pb) ->
    Src = z_lib:get_value(Info, src, ""),
    RoleUid = role_lib:get_uid(Attr),
    ServerId = uid_lib:get_server(RoleUid),
    TableKeys = z_db_lib:transformation_tablekey([
        {{ServerId, '{ModuleName}', RoleUid, none}}
    ]),
    Reply = case z_db_lib:handle(fun {ModuleName}_db:update/2, {{}}, TableKeys) of
        ok ->
            z_log:info(?MODULE, ?FUNCTION_NAME, "{ModuleName}_port_update", [
                {{"role_uid", RoleUid}},
                {{"client_pb", Pb}}
            ]),
            pb_{ModuleName}:init_sc_{ModuleName}_update();
        Err ->
            game_lib:error_msg(Err)
    end,
    {{ok, [], Info, Reply}}.

%%%===================LOCAL FUNCTIONS==================
%% ----------------------------------------------------
%%
%% ----------------------------------------------------
"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return f"生成 {file_path} 成功"

def generate_port_cfg(DirPath, ModuleName, Desc):
    """生成 xxx_port.cfg 文件（对应auto_port_cfg.erl）"""
    file_path = os.path.join(DirPath, f"{ModuleName}_port.cfg")
    content = f"""%%{Desc}获取信息
{{template, _ZM_SESSION, {{{{Project, "/game/{ModuleName}_port/get_data"}},
    [
        {{server_port, reassembly_msg, []}},
        {{{ModuleName}_port, get_data, []}}
    ]}}
}}.
%%更新数据
{{template, _ZM_SESSION, {{{{Project, "/game/{ModuleName}_port/update"}},
    [
        {{server_port, reassembly_msg, []}},
        {{reconnect_db, msg_start, []}},
        {{{ModuleName}_port, update, []}},
        {{reconnect_db, msg_end, []}}
    ]}}
}}.
"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return f"生成 {file_path} 成功"

def parse_record_and_append(FileName):
    """解析erl文件中的-record，生成get/set函数并追加（对应auto_reco.erl）"""
    # 读取文件内容
    with open(FileName, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 正则匹配-record定义：-record(xxx, {字段1, 字段2, ...}).
    record_pattern = re.compile(r'-record\((\w+),\s*\{\s*(.*?)\s*\}\);', re.DOTALL)
    matches = record_pattern.findall(content)
    
    if not matches:
        return f"{FileName} 中未找到-record定义，无需追加内容"
    
    result = []
    for RecoName, KeyStr in matches:
        # 提取字段名（过滤注释、空行）
        KeyList = []
        for line in KeyStr.split('\n'):
            # 去掉注释和空白
            line = line.strip().split('%')[0].strip()
            if line and line not in [',', '{', '}']:
                # 提取字段名（处理 "字段名 = 默认值" 格式）
                key = line.split('=')[0].strip().rstrip(',')
                if key:
                    KeyList.append(key)
        
        if not KeyList:
            continue
        
        # 生成export语句
        export_parts = ['init/0']
        for key in KeyList:
            export_parts.append(f"get_{key}/1")
            export_parts.append(f"set_{key}/2")
        export_str = f"\n-export([{', '.join(export_parts)}]).\n\n"
        
        # 生成init函数
        init_str = f"init()->#{RecoName}{{}}.\n\n"
        
        # 生成get函数
        get_str = ""
        for key in KeyList:
            get_str += f"get_{key}(Reco)->Reco#{RecoName}.{key}.\n"
        
        # 生成set函数
        set_str = "\n"
        for key in KeyList:
            set_str += f"set_{key}(Reco,V)->Reco#{RecoName}{{{key}=V}}.\n"
        
        # 拼接所有内容
        append_str = export_str + init_str + get_str + set_str
        
        # 追加到文件
        with open(FileName, 'a', encoding='utf-8') as f:
            f.write(append_str)
        
        result.append(f"为 {FileName} 的 {RecoName} 追加get/set函数成功")
    
    return "\n".join(result) if result else f"{FileName} 中无有效-record字段"

# ===================== GUI界面函数 =====================
def on_start_click():
    """点击开始按钮执行生成逻辑"""
    # 获取输入框内容
    DirPath = entry_dir.get().strip()
    ModuleName = entry_module.get().strip()
    Desc = entry_desc.get().strip()
    
    # 输入校验
    if not DirPath or not ModuleName or not Desc:
        messagebox.showerror("错误", "请填写所有输入框！")
        return
    
    # 清空日志
    text_log.delete(1.0, tk.END)
    
    try:
        # 确保目录存在
        ensure_dir_exists(DirPath)
        
        # 执行所有生成函数
        log_messages = []
        log_messages.append(generate_db_erl(DirPath, ModuleName, Desc))
        log_messages.append(generate_db_cfg(DirPath, ModuleName, Desc))
        log_messages.append(generate_lib_erl(DirPath, ModuleName, Desc))
        log_messages.append(generate_pb_proto(DirPath, ModuleName, Desc))
        log_messages.append(generate_port_erl(DirPath, ModuleName, Desc))
        log_messages.append(generate_port_cfg(DirPath, ModuleName, Desc))
        
        # 解析-record并追加get/set函数（对应auto_reco.erl）
        lib_erl_path = os.path.join(DirPath, f"{ModuleName}.erl")
        log_messages.append(parse_record_and_append(lib_erl_path))
        
        # 显示日志
        text_log.insert(tk.END, "\n".join(log_messages))
        messagebox.showinfo("成功", "所有文件生成完成！")
    
    except Exception as e:
        error_msg = f"生成失败：{str(e)}"
        text_log.insert(tk.END, error_msg)
        messagebox.showerror("错误", error_msg)

def create_gui():
    """创建GUI界面"""
    root = tk.Tk()
    root.title("Erlang代码自动生成工具")
    root.geometry("800x600")
    
    # 1. 目录路径输入框
    label_dir = tk.Label(root, text="目录路径：")
    label_dir.place(x=20, y=20)
    global entry_dir
    entry_dir = tk.Entry(root, width=80)
    entry_dir.place(x=100, y=20)
    entry_dir.insert(0, "D:/erlang_code")  # 默认值
    
    # 2. 模块名输入框
    label_module = tk.Label(root, text="模块名：")
    label_module.place(x=20, y=60)
    global entry_module
    entry_module = tk.Entry(root, width=80)
    entry_module.place(x=100, y=60)
    entry_module.insert(0, "player_info")  # 默认值
    
    # 3. 描述输入框
    label_desc = tk.Label(root, text="功能描述：")
    label_desc.place(x=20, y=100)
    global entry_desc
    entry_desc = tk.Entry(root, width=80)
    entry_desc.place(x=100, y=100)
    entry_desc.insert(0, "玩家信息管理")  # 默认值
    
    # 4. 开始按钮
    btn_start = tk.Button(root, text="开始生成", command=on_start_click, width=20, height=2)
    btn_start.place(x=350, y=140)
    
    # 5. 日志显示框
    label_log = tk.Label(root, text="生成日志：")
    label_log.place(x=20, y=200)
    global text_log
    text_log = scrolledtext.ScrolledText(root, width=90, height=25)
    text_log.place(x=20, y=230)
    
    root.mainloop()

# ===================== 程序入口 =====================
if __name__ == "__main__":
    create_gui()