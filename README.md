# AI 模拟面试官平台 (AI Interviewer)

这是一个基于 Web 的沉浸式 AI 模拟面试工具。项目通过接入火山引擎（豆包大模型）的文本和多模态视觉模型，配合前端原生 Web Speech API 及媒体流技术，为用户打造了一个真实的面试模拟环境。

## 🌟 核心功能

1. **沉浸式交互界面**：
   - 居中的“Siri风格”呼吸圆球代表 AI 面试官，结合流式输出（SSE）和毛玻璃气泡弹窗，提供极佳的交互反馈。
   - 左右分屏设计，右侧实时显示被面试者的摄像头画面。
2. **多模态 AI 情绪助理与本地人脸检测**：
   - 侧边栏搭载 AI 面试助理，结合本地人脸检测（支持 MTCNN 或 Haar 动态切换）与火山引擎多模态视觉模型。
   - 本地模型负责实时检测人脸状态（防止大模型冗余判断），AI 助理专注情绪与状态分析（如紧张、走神等），并进行 UI 去重，避免重复弹窗打扰用户。
   - 采用适中的检测严格度，平衡监考需求与用户体验，温和友好地提示与鼓励候选人。
3. **双阶段限时系统**：
   - 模拟真实的面试压力，每一轮回答均设有“思考阶段”和“回答阶段”双倒计时。
   - 带有 SVG 环形进度条警告，超时将自动交卷或自动跳过。
4. **语音转文字 (Speech-to-Text)**：
   - 接入浏览器原生的 Web Speech API，一键录音实时转写，解放双手。
5. **面试综合评估报告**：
   - 面试结束后，AI 将基于整场对话历史，生成多维度的评估报告。
   - 包含：综合得分、ECharts 雷达图（专业技能、沟通表达、逻辑思维等）、整体点评以及优势/改进建议。

## 🛠️ 技术栈

- **前端**：HTML5, CSS3, 原生 JavaScript (Vanilla JS), WebRTC (摄像头), Web Speech API, ECharts
- **后端**：Python 3.10, FastAPI, Uvicorn, MTCNN/Haar Cascade (本地人脸检测), TensorFlow (可选)
- **AI 接口**：火山引擎 - 豆包大模型 (Volcengine SDK / REST API)

## 🚀 快速开始

### 1. 环境准备

请确保您已安装 **Python 3.8+** 环境。（如果选择使用 `mtcnn` 作为人脸检测器，因 TensorFlow 依赖版本要求，推荐使用 **Python 3.10** 以避免兼容性问题）。

### 2. 克隆/进入项目目录

```bash
cd ai_interview
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制环境示例文件并重命名为 `.env`：

```bash
cp .env.example .env
```

打开 `.env` 文件，填入您的火山引擎配置信息：

```env
DOUBAO_API_KEY=您的火山引擎API_KEY
DOUBAO_ENDPOINT_ID=用于主对话的文本模型接入点ID (如 doubao-pro 等)
DOUBAO_LITE_ENDPOINT_ID=用于视觉情绪分析的多模态Lite模型接入点ID (默认：doubao-seed-2-0-lite-260215)
```

**可选配置人脸检测模型：**
在项目根目录可找到或创建 `configs/config.yaml` 文件来动态切换人脸检测器：

```yaml
face_detector: "haar"  # 默认使用 "haar" 避免引入重度依赖；可选: "mtcnn"
```
> **注意：** 默认使用轻量级的 Haar Cascade 算法。如果你将 `face_detector` 设置为了 `mtcnn`，你需要额外安装 MTCNN 与 TensorFlow 依赖（参见 `requirements.txt` 里的注释）。

### 5. 启动服务

使用 Uvicorn 启动 FastAPI 后端服务：

```bash
python -m uvicorn app:app --reload
```

### 6. 访问应用

打开浏览器（推荐使用 Chrome 或 Edge 以获得最佳的语音识别体验），访问：
**<http://127.0.0.1:8000>**

> **注意**：初次访问时浏览器会请求摄像头和麦克风权限，请点击“允许”以确保视频画面和语音输入功能正常工作。

## 📂 项目结构

```text
ai_interview/
├── app.py                 # FastAPI 后端核心代码（处理聊天、情绪分析、报告生成）
├── requirements.txt       # Python 依赖包
├── .env                   # 环境变量配置（需自行创建并填写）
├── .env.example           # 环境变量示例文件
├── .gitignore             # Git 忽略配置
├── configs/               # 配置文件目录
│   └── config.yaml        # 项目参数配置（人脸检测器模型切换等）
├── utils/                 # 工具类目录
│   └── face_detector.py   # 封装本地人脸检测（MTCNN/Haar）
├── docs/                  # 存放项目设计或需求文档
│   └── prd_and_architecture.md
└── html/                  # 前端静态文件目录
    ├── index.html         # 页面骨架
    ├── style.css          # 页面样式（包含动画与响应式设计）
    └── script.js          # 前端交互逻辑（流式接收、倒计时、摄像头截帧、UI 去重等）
```

