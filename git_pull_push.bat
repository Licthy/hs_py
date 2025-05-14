@echo off
rem 设置为 UTF-8 编码
chcp 65001 > nul 

setlocal enabledelayedexpansion

echo 开始同步代码...

rem 拉取远程更新
echo 正在拉取最新代码...
git pull
if !errorlevel! neq 0 (
    echo 拉取失败，请检查网络连接或远程仓库状态
    goto :end
)

rem 检查是否有变更
echo 正在检查变更...
git status --porcelain | findstr /r "^ M\|^M " > nul
if !errorlevel! equ 0 (
    echo 发现变更，准备提交...
    
    rem 添加所有变更
    git add .
    
    rem 显示状态
    git status
    
    rem 提交变更（使用动态提交信息）
    set /p commit_msg=请输入提交信息（默认: 自动提交）: 
    if "!commit_msg!"=="" set commit_msg=自动提交
    git commit -m "!commit_msg!"
    
    rem 推送变更
    echo 正在推送到远程仓库...
    git push
    if !errorlevel! neq 0 (
        echo 推送失败，请检查权限或远程仓库状态
        goto :end
    )
    
    echo 代码同步完成！
) else (
    echo 没有发现变更，无需提交
)

:end
pause