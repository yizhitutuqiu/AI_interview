# AI 面试官 - 极简部署指南

## 1. 下载并运行一键安装脚本
系统已内置全自动环境配置脚本，它会**自动帮你下载项目代码**、安装 Git、Miniconda、创建 Python 环境并安装所有依赖。

你可以将安装脚本单独下载到你希望安装项目的任意空文件夹中，然后根据你的操作系统双击或在终端运行：

- **Windows 用户**:
  下载并双击运行 `install.bat` 
  *(如果一闪而过或报错，请右键选择“以管理员身份运行”)*

- **macOS / Linux 用户**:
  下载 `install.sh` 并打开终端，首先使用 `cd` 命令进入存放该脚本的目录（例如你下载到了 Downloads 文件夹，就先执行 `cd ~/Downloads`），然后执行：
  ```bash
  chmod +x install.sh
  ./install.sh
  ```

*(执行完毕后，当前目录下会自动生成一个名为 `ai_interview` 的文件夹)*

---

## 2. 填写 API 密钥
进入刚刚生成的 `ai_interview` 项目目录，你会发现里面自动生成了一个 `.env` 隐藏文件。
请用记事本或编辑器打开它，并前往 [火山引擎官网](https://console.volcengine.com/ark) 申请豆包大模型的 API Key，将其填入：

```env
DOUBAO_API_KEY=你的API_KEY（仅填写本项即可，其余无需修改）
```

申请api_key的详细流程可以参考：[豆包_API配置方式.docx](ai_interview/docs/豆包_API配置方式.docx)
此文档中有详细图片流程。
---

## 3. 启动并访问
一切就绪后，在命令行中输入以下命令启动服务（**注意：以后每次你想启动服务时，都必须先打开终端/命令行，使用 `cd` 命令进入 `ai_interview` 这个项目文件夹！**）：

```bash
# 1. 确保你当前在 ai_interview 目录下
cd ai_interview

# 2. 激活虚拟环境并启动
conda activate ai_interview
python -m uvicorn app:app --reload
```
随后打开浏览器访问 [http://127.0.0.1:8000](http://127.0.0.1:8000) 即可开始体验！

> **注意**：如果一键脚本运行失败（如网络原因导致下载中断），请参考 [手动部署文档](ai_interview/docs/docs/INSTALL.md) 逐步排查并安装。