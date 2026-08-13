# HS App Launcher

一个 Windows 场景化程序启动器。把常用软件按“听歌”“游戏”“办公”等页签归组，点击一次即可启动当前页签和“必起”页签中的全部已启用程序。

## 使用

- 双击 `run.bat` 从源码运行。
- 双击 `dist\HSStartApp\HSStartApp.exe` 运行打包版。
- 点击“添加程序”选择程序或快捷方式，也可把 `.exe`、`.lnk`、`.bat`、`.cmd`、`.com`、`.url`、`.msc` 文件直接拖入列表。
- 勾选“管理员”后，该项启动时会请求 Windows 管理员授权。
- 右键页签可改名、复制、删除和调整顺序；也可以直接拖动页签排序。“必起”页签固定在第一位，不能删除或改名。
- 程序可拖动排序，也可用“上移”“下移”；双击程序可在资源管理器中定位文件。
- 左侧“打开配置文件夹”可直接定位当前配置文件。

配置保存在 `%APPDATA%\HSStartApp\config.json`，会记录所有场景、程序、管理员选项、主题、窗口位置和上次停留场景。新版默认使用浅色主题，仍可手动切换深色或自动模式。

## 构建

```powershell
python -m pip install -r requirements.txt
.\build.bat
```

Windows 图标由 `generate_icon.py` 从 `app.png` 生成。重新生成需要 Pillow：

```powershell
python -m pip install Pillow
python generate_icon.py
```
