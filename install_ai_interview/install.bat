@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo       AI 面试官 - Windows 一键安装脚本      
echo ==========================================
echo.

:: 1. 检查并安装 Git
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo 未检测到 Git，正在尝试自动下载安装...
    curl -L -o Git-Installer.exe "https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe"
    if %errorlevel% neq 0 (
        echo 错误: Git 下载失败，请手动前往 https://git-scm.com/ 下载安装。
        pause
        exit /b 1
    )
    echo 正在静默安装 Git...
    start /wait Git-Installer.exe /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
    del Git-Installer.exe
    echo Git 安装完成！建议安装后重新运行此脚本。
) else (
    echo Git 已安装。
)
echo.

:: 2. 克隆项目代码
set REPO_URL=https://github.com/yourusername/ai_interview.git
set PROJECT_DIR=ai_interview

if not exist "%PROJECT_DIR%" (
    echo 正在从 GitHub 下载项目代码...
    git clone %REPO_URL%
    cd %PROJECT_DIR%
) else (
    echo 项目目录已存在，正在尝试更新代码...
    cd %PROJECT_DIR%
    git pull
)
echo.

:: 3. 检查并安装 Miniconda
where conda >nul 2>nul
if %errorlevel% neq 0 (
    if not exist "%USERPROFILE%\miniconda3\Scripts\conda.exe" (
        echo 未检测到 Conda，正在自动下载 Miniconda...
        curl -L -o Miniconda3.exe "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
        if %errorlevel% neq 0 (
            echo 错误: Miniconda 下载失败，请手动前往官网下载。
            pause
            exit /b 1
        )
        echo 正在静默安装 Miniconda...
        start /wait "" Miniconda3.exe /InstallationType=JustMe /RegisterPython=0 /S /D=%USERPROFILE%\miniconda3
        del Miniconda3.exe
        echo Miniconda 安装完成！
    )
    :: 临时将 conda 加入环境变量以便当前脚本使用
    set PATH=%USERPROFILE%\miniconda3\Scripts;%USERPROFILE%\miniconda3\condabin;%PATH%
) else (
    echo Conda 已安装。
)
echo.

:: 3. 初始化并创建环境
echo 正在配置 Conda 环境...
call "%USERPROFILE%\miniconda3\Scripts\activate.bat" base

set ENV_NAME=ai_interview
call conda info --envs | findstr /b /c:"%ENV_NAME% " >nul
if %errorlevel% neq 0 (
    echo 正在创建 conda 虚拟环境: %ENV_NAME% (Python 3.10)...
    call conda create -n %ENV_NAME% python=3.10 -y
) else (
    echo 虚拟环境 %ENV_NAME% 已存在。
)

echo 激活环境 %ENV_NAME%...
call conda activate %ENV_NAME%
echo.

:: 4. 安装依赖
echo 正在安装 Python 依赖 (requirements.txt)...
if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    echo 警告: 未找到 requirements.txt 文件！
)
echo.

:: 5. 配置变量
echo 正在准备环境变量配置文件...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo .env 文件已从 .env.example 复制。
    ) else (
        echo 警告: 未找到 .env.example 文件！
    )
) else (
    echo .env 文件已存在，跳过复制。
)
echo.

echo ==========================================
echo 部署脚本执行完毕！
echo ==========================================
echo.
echo 接下来的步骤：
echo 1. 请编辑项目目录下的 .env 文件，填入你的火山引擎 API 密钥。
echo 2. 在当前窗口输入以下命令启动服务：
echo    conda activate ai_interview
echo    python -m uvicorn app:app --reload
echo 3. 启动后，在浏览器访问 http://127.0.0.1:8000
echo.
pause
