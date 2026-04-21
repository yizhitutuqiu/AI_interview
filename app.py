import os
import json
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from volcenginesdkarkruntime import Ark
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# ================= 配置读取 =================
DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY", "YOUR_DOUBAO_API_KEY")
DOUBAO_ENDPOINT_ID = os.getenv("DOUBAO_ENDPOINT_ID", "YOUR_ENDPOINT_ID")
DOUBAO_LITE_ENDPOINT_ID = os.getenv("DOUBAO_LITE_ENDPOINT_ID", "doubao-seed-2-0-lite-260215")
# ==========================================

app = FastAPI(title="AI Interview Tool")

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义请求体结构，新增了公司类型和岗位角色以及限时参数
class ChatRequest(BaseModel):
    company_type: str
    job_role: str
    think_time: int
    answer_time: int
    messages: List[Dict[str, str]]

class EmotionRequest(BaseModel):
    image: str # Base64 格式的图片数据

@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    # 动态构建系统提示词，植入面试场景和限时要求
    system_prompt = (
        f"你是一个专业的AI面试官。目前代表【{request.company_type}】面试候选人的【{request.job_role}】岗位。\n"
        f"请根据候选人的回答进行专业、客观的追问、点评。你的目标是考察候选人的专业能力和软技能。\n"
        f"每次只问一个问题，不要长篇大论，语气自然、专业、贴合该类型公司和岗位的实际工作背景。\n"
        f"【重要规则】：由于系统给候选人设置了严格的时限（思考时间：{request.think_time}秒，回答时间：{request.answer_time}秒），"
        f"所以你的提问必须简洁明了，确保候选人能在上述短时间内完成思考并作答。"
    )
    
    system_message = {
        "role": "system", 
        "content": system_prompt
    }
    
    # 组装完整的对话历史
    messages = [system_message] + request.messages
    
    if DOUBAO_API_KEY == "YOUR_DOUBAO_API_KEY" or DOUBAO_ENDPOINT_ID == "YOUR_ENDPOINT_ID":
        return JSONResponse(
            status_code=500, 
            content={"error": "系统未配置：请先在 .env 文件中填写 DOUBAO_API_KEY 和 DOUBAO_ENDPOINT_ID。"}
        )

    try:
        client = Ark(api_key=DOUBAO_API_KEY)
        
        # 启用流式输出 (stream=True)
        stream = client.chat.completions.create(
            model=DOUBAO_ENDPOINT_ID,
            messages=messages,
            stream=True
        )
        
        def generate():
            try:
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    content = chunk.choices[0].delta.content
                    if content:
                        # 构造 SSE (Server-Sent Events) 格式的数据
                        yield f"data: {json.dumps({'text': content})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/report")
async def generate_report(request: ChatRequest):
    if DOUBAO_API_KEY == "YOUR_DOUBAO_API_KEY" or DOUBAO_ENDPOINT_ID == "YOUR_ENDPOINT_ID":
        return JSONResponse(
            status_code=500, 
            content={"error": "系统未配置：请先在 .env 文件中填写 DOUBAO_API_KEY 和 DOUBAO_ENDPOINT_ID。"}
        )

    # 构造用于生成评估报告的系统提示词，强制要求返回 JSON 格式
    system_prompt = (
        f"你是一个资深的HR和技术面试官。请根据以下候选人与AI面试官的对话历史，对候选人进行全面的面试评估。\n"
        f"候选人应聘的是【{request.company_type}】的【{request.job_role}】岗位。\n"
        f"请必须以严格的 JSON 格式输出你的评估结果，不要包含任何 markdown 代码块标记(如 ```json)或其他多余说明文字。\n"
        f"JSON 结构必须如下：\n"
        "{\n"
        '  "total_score": 85, // 综合得分，0-100的整数\n'
        '  "dimensions": {\n'
        '    "professional": 80, // 专业技能得分 0-100\n'
        '    "communication": 90, // 沟通表达能力 0-100\n'
        '    "logic": 85, // 逻辑思维 0-100\n'
        '    "adaptability": 80, // 应变与抗压能力 0-100\n'
        '    "culture_fit": 85 // 企业文化匹配度 0-100\n'
        "  },\n"
        '  "overall_comment": "这里是一段针对候选人的综合点评（大约100字左右）。",\n'
        '  "strengths": ["优点1", "优点2", "优点3"], // 亮点列表\n'
        '  "weaknesses": ["改进建议1", "改进建议2"] // 不足与改进建议列表\n'
        "}"
    )
    
    # 提取历史对话内容
    conversation_history = "【对话历史记录】：\n"
    for msg in request.messages:
        role_name = "面试官" if msg["role"] == "assistant" else "候选人"
        # 忽略掉原始的 system message
        if msg["role"] != "system":
            conversation_history += f"{role_name}：{msg['content']}\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": conversation_history}
    ]

    try:
        client = Ark(api_key=DOUBAO_API_KEY)
        
        response = client.chat.completions.create(
            model=DOUBAO_ENDPOINT_ID,
            messages=messages,
            # 某些模型支持 response_format={"type": "json_object"}，为稳妥起见这里主要靠 prompt 约束
        )
        
        reply_content = response.choices[0].message.content.strip()
        
        # 简单清理可能存在的 markdown 标记
        if reply_content.startswith("```json"):
            reply_content = reply_content[7:]
        if reply_content.startswith("```"):
            reply_content = reply_content[3:]
        if reply_content.endswith("```"):
            reply_content = reply_content[:-3]
            
        report_data = json.loads(reply_content.strip())
        return JSONResponse(content=report_data)
        
    except json.JSONDecodeError as e:
        return JSONResponse(status_code=500, content={"error": f"JSON解析失败，AI返回格式错误: {str(e)}\n{reply_content}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/analyze_emotion")
async def analyze_emotion(request: EmotionRequest):
    if DOUBAO_API_KEY == "YOUR_DOUBAO_API_KEY" or DOUBAO_ENDPOINT_ID == "YOUR_ENDPOINT_ID":
        return JSONResponse(status_code=500, content={"error": "系统未配置 API Key"})

    try:
        # Lite 模型的 Endpoint，固定为火山引擎给定的 Lite 视觉模型 endpoint
        # 注意：这里直接调用 HTTP API，而非 SDK，因为要求使用 lite 多模态
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {DOUBAO_API_KEY}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            "你是一个友好的AI面试助理。我将给你看一张被面试者在面试过程中的摄像头截图。"
            "你需要判断被试者的情绪（紧张、放松、沮丧、走神等），并判断是否需要安慰、鼓励或提醒（比如提醒不要东张西望）。"
            "你的回复必须是一句简短的话（不超过30个字）。语气要非常友好、温柔、有亲和力。"
            "如果你觉得候选人状态很好，不需要特别的提醒，请直接返回大写的 'NONE'，不要有其他任何字符。"
            "输出格式必须是 JSON，结构为：{\"message\": \"你的提示语\", \"type\": \"info|warning|success\"}"
        )

        payload = {
            "model": DOUBAO_LITE_ENDPOINT_ID,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": system_prompt + "\n\n请分析我的状态并给出助理提示。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": request.image
                            }
                        }
                    ]
                }
            ]
        }

        # 打印 payload 排查问题
        # print("Payload sending to Ark API:", json.dumps(payload, ensure_ascii=False)[:200] + "...")

        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            resp_data = response.json()
            content = resp_data["choices"][0]["message"]["content"].strip()
            
            if content == "NONE" or content == '"NONE"':
                return {"message": "NONE"}
                
            # 清理可能的 markdown
            if content.startswith("```json"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            try:
                result = json.loads(content.strip())
                return result
            except json.JSONDecodeError:
                # 如果没按要求返回 JSON，就把纯文本包起来
                return {"message": content, "type": "info"}
        else:
            return JSONResponse(status_code=response.status_code, content={"error": response.text})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# 挂载前端静态文件 (必须放在所有 API 路由之后)
html_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html")
app.mount("/", StaticFiles(directory=html_dir, html=True), name="html")

# 启动服务器的入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
