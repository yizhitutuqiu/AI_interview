import os
import json
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
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

class ReportRequest(BaseModel):
    company_type: str
    job_role: str
    think_time: int
    answer_time: int
    messages: List[Dict[str, str]]
    assistant_observations: List[str] = []

class EmotionRequest(BaseModel):
    image: str # Base64 格式的图片数据

@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    # 计算用户发言的轮数（保底机制判断）
    user_turns = sum(1 for msg in request.messages if msg.get("role") == "user")
    
    # 动态构建系统提示词，植入面试场景和限时要求
    system_prompt = (
        f"你是一个专业的AI面试官。目前代表【{request.company_type}】面试候选人的【{request.job_role}】岗位。\n"
        f"当前面试进度：你已经向候选人提问了 {user_turns} 轮。\n"
        f"请根据候选人的回答进行专业、客观的追问、点评。你的目标是考察候选人的专业能力和软技能。\n"
        f"每次只问一个问题，不要长篇大论，语气自然、专业、贴合该类型公司和岗位的实际工作背景。\n"
        f"【重要规则1】：由于系统给候选人设置了严格的时限（思考时间：{request.think_time}秒，回答时间：{request.answer_time}秒），"
        f"所以你的提问必须简洁明了，确保候选人能在上述短时间内完成思考并作答。\n"
        f"【重要规则2（结束机制）】：当前候选人已经回答了 {user_turns} 轮问题。如果 {user_turns} 小于 5，你必须继续提问，绝对不能结束面试。如果 {user_turns} 大于或等于 5，你可以根据候选人的回答质量自主决定是否继续深入提问，或者选择结束面试。当你决定结束面试时，你必须在你的回复末尾附加上精确的字符串 [INTERVIEW_FINISHED] 作为结束标记。例如：'好的，感谢您的回答，今天的面试就到这里。我们会尽快通知您结果。[INTERVIEW_FINISHED]'"
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
async def generate_report(request: ReportRequest):
    if DOUBAO_API_KEY == "YOUR_DOUBAO_API_KEY" or DOUBAO_ENDPOINT_ID == "YOUR_ENDPOINT_ID":
        return JSONResponse(
            status_code=500, 
            content={"error": "系统未配置：请先在 .env 文件中填写 DOUBAO_API_KEY 和 DOUBAO_ENDPOINT_ID。"}
        )

    # 提取行为观察记录
    obs_text = "\n".join([f"- {obs}" for obs in request.assistant_observations]) if request.assistant_observations else "无特别行为观察记录"

    # 构造用于生成评估报告的系统提示词，强制要求返回 JSON 格式
    system_prompt = (
        f"你是一个资深的HR和技术面试官。请根据以下候选人与AI面试官的对话历史，以及AI助理对候选人在面试过程中的行为状态观察，对候选人进行全面的面试评估。\n"
        f"候选人应聘的是【{request.company_type}】的【{request.job_role}】岗位。\n"
        f"【AI助理行为观察记录】:\n{obs_text}\n\n"
        f"请综合候选人的回答内容以及行为表现（如是否紧张、是否走神等），以严格的 JSON 格式输出你的评估结果，不要包含任何 markdown 代码块标记(如 ```json)或其他多余说明文字。\n"
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
            "如果你觉得候选人状态很好，不需要特别的提醒，你可以给出一句简短的鼓励（如：状态不错，继续保持！）。"
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
        # 延长超时时间到 30 秒，多模态模型处理图片有时会比较慢
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        try:
            response_json = response.json()
        except Exception:
            response_json = response.text
                
            if response.status_code != 200:
                print(f"火山引擎接口报错: HTTP {response.status_code} - {response_json}")
                return JSONResponse(status_code=500, content={"error": "Vision API Error", "details": response_json})

            # 解析结果
            try:
                content = response_json["choices"][0]["message"]["content"]
                print(f"[Emotion API] 大模型原始回复: {content}")
                
                if not content:
                    return {"message": "状态不错，继续保持！", "type": "success"}
                
                content = content.strip()
                if content == "NONE" or content == '"NONE"':
                    return {"message": "状态不错，继续保持！", "type": "success"}
                    
                # 处理大模型有时可能包裹的 markdown
                if content.startswith("```json"): content = content[7:]
                if content.startswith("```"): content = content[3:]
                if content.endswith("```"): content = content[:-3]
                
                # 尝试将回答解析为 JSON 格式
                result = json.loads(content.strip())
                return {
                    "message": result.get("message", "NONE"),
                    "type": result.get("type", "info")
                }
            except json.JSONDecodeError:
                # 如果大模型没有返回 JSON，而是返回了纯文本
                if "NONE" in content.upper() or len(content.strip()) < 2:
                    return {"message": "状态不错，继续保持！", "type": "success"}
                else:
                    return {"message": content.strip(), "type": "info"}
            except KeyError as e:
                print(f"解析火山引擎返回值失败: {e}, 原始返回值: {response_json}")
                return {"message": "状态不错，继续保持！", "type": "success"}
                
    except Exception as e:
        print(f"请求火山引擎发生异常: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"请求火山引擎失败: {str(e)}"})

# 挂载前端静态文件 (必须放在所有 API 路由之后)
class NoCacheStaticFiles(StaticFiles):
    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False
        
    def file_response(self, full_path: os.PathLike, stat_result: os.stat_result, scope, status_code: int = 200) -> FileResponse:
        response = super().file_response(full_path, stat_result, scope, status_code)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

html_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html")
app.mount("/", NoCacheStaticFiles(directory=html_dir, html=True), name="html")

# 启动服务器的入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
