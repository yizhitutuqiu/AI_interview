import base64
import os
import json
import logging
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from volcenginesdkarkruntime import Ark
from dotenv import load_dotenv
import asyncio
from utils.face_detector import detect_faces_from_base64

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_interview")

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

    client = Ark(api_key=DOUBAO_API_KEY)
    loop = asyncio.get_event_loop()

    # 1. 提取问答对
    qa_pairs = []
    current_q = None
    for msg in request.messages:
        if msg["role"] == "system":
            continue
        if msg["role"] == "assistant":
            current_q = msg["content"]
        elif msg["role"] == "user" and current_q:
            qa_pairs.append((current_q, msg["content"]))
            current_q = None

    # 2. 定义异步单题打分任务
    async def score_qa_pair_async(question, answer):
        prompt = (
            f"你是一个专业的面试评估专家。请针对以下【单一问答回合】进行独立打分。\n"
            f"候选人应聘的是【{request.company_type}】的【{request.job_role}】岗位。\n"
            f"【面试官提问】：{question}\n"
            f"【候选人回答】：{answer}\n\n"
            f"请参照STAR法则评估候选人的回答质量，给出0-100的各项分数，并给出一个【置信度权重(0.0-1.0)】。\n"
            f"置信度说明：如果该回答非常详细、展现了明显的能力特征，置信度设为0.8-1.0；如果回答极其简短、无关痛痒或跑题，置信度设为0.1-0.4。\n"
            f"必须严格返回JSON格式如下：\n"
            "{\n"
            '  "confidence": 0.85,\n'
            '  "dimensions": {\n'
            '    "professional": 80,\n'
            '    "communication": 90,\n'
            '    "logic": 85,\n'
            '    "adaptability": 80,\n'
            '    "culture_fit": 85\n'
            "  },\n"
            '  "comment": "对本题回答的简短点评"\n'
            "}"
        )
        try:
            response = await loop.run_in_executor(
                None, 
                lambda: client.chat.completions.create(
                    model=DOUBAO_ENDPOINT_ID,
                    messages=[{"role": "system", "content": prompt}]
                )
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            return json.loads(content.strip())
        except Exception as e:
            logger.error(f"逐题打分失败: {e}")
            return None

    # 3. 并发执行逐题打分
    tasks = [score_qa_pair_async(q, a) for q, a in qa_pairs]
    per_question_results = await asyncio.gather(*tasks)
    
    # 4. 过滤有效结果并计算加权平均分
    valid_results = [res for res in per_question_results if res and "confidence" in res and "dimensions" in res]
    
    final_dimensions = {
        "professional": 0, "communication": 0, "logic": 0, "adaptability": 0, "culture_fit": 0
    }
    total_confidence = 0.0
    
    if valid_results:
        for res in valid_results:
            conf = res.get("confidence", 0.5)
            total_confidence += conf
            for dim in final_dimensions.keys():
                final_dimensions[dim] += res["dimensions"].get(dim, 0) * conf
                
        if total_confidence > 0:
            for dim in final_dimensions.keys():
                final_dimensions[dim] = int(final_dimensions[dim] / total_confidence)
        else:
            final_dimensions = {k: 0 for k in final_dimensions}
    else:
        # 降级处理
        final_dimensions = {"professional": 60, "communication": 60, "logic": 60, "adaptability": 60, "culture_fit": 60}

    overall_score = int(sum(final_dimensions.values()) / 5) if final_dimensions else 0

    # 5. 综合评价 (大模型最终总结)
    obs_text = "\n".join([f"- {obs}" for obs in request.assistant_observations]) if request.assistant_observations else "无特别行为观察记录"
    per_q_comments = "\n".join([f"- 问答回合点评: {res.get('comment', '')} (置信度: {res.get('confidence', 0)})" for res in valid_results])
    
    final_summary_prompt = (
        f"你是一个资深的HR和技术面试官。候选人应聘的是【{request.company_type}】的【{request.job_role}】岗位。\n"
        f"我已经通过逐题评估算法得出了候选人的各项加权最终得分，如下：\n"
        f"综合得分: {overall_score}\n"
        f"维度得分: {json.dumps(final_dimensions, ensure_ascii=False)}\n\n"
        f"以下是候选人的各题独立点评细节：\n{per_q_comments}\n\n"
        f"以下是【AI助理行为观察记录】(包含走神、紧张等状态):\n{obs_text}\n\n"
        f"请基于上述的最终得分、逐题点评和行为观察，为该候选人生成最终的文字评估报告。\n"
        f"必须严格返回JSON格式如下，不要包含任何 markdown 标记：\n"
        "{\n"
        '  "overall_comment": "这里是一段针对候选人的综合点评（结合各项得分和行为表现，大约150字左右）。",\n'
        '  "strengths": ["优点1", "优点2", "优点3"], // 结合逐题点评提炼的亮点\n'
        '  "weaknesses": ["改进建议1", "改进建议2"] // 结合逐题点评和行为观察提炼的不足\n'
        "}"
    )

    try:
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=DOUBAO_ENDPOINT_ID,
                messages=[{"role": "system", "content": final_summary_prompt}]
            )
        )
        reply_content = response.choices[0].message.content.strip()
        
        if reply_content.startswith("```json"): reply_content = reply_content[7:]
        if reply_content.startswith("```"): reply_content = reply_content[3:]
        if reply_content.endswith("```"): reply_content = reply_content[:-3]
            
        report_data = json.loads(reply_content.strip())
        
        # 组装最终结果
        final_report = {
            "total_score": overall_score,
            "dimensions": final_dimensions,
            "overall_comment": report_data.get("overall_comment", "无"),
            "strengths": report_data.get("strengths", []),
            "weaknesses": report_data.get("weaknesses", [])
        }
        return JSONResponse(content=final_report)
        
    except Exception as e:
        logger.error(f"生成最终总结失败: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"生成最终总结失败: {str(e)}"})

@app.post("/api/detect_face")
async def detect_face(request: Request):
    """
    高频人脸检测接口：专门用于快速检测画面中是否有人脸，或者是否有多个人脸。
    """
    try:
        data = await request.json()
        base64_image = data.get("image")
        
        if not base64_image:
            return JSONResponse(status_code=400, content={"error": "未提供图片数据"})
        
        # 移除 base64 的 data:image/jpeg;base64, 前缀
        if "," in base64_image:
            base64_image_clean = base64_image.split(",")[1]
        else:
            base64_image_clean = base64_image
            
        loop = asyncio.get_event_loop()
        face_count = await loop.run_in_executor(None, detect_faces_from_base64, base64_image_clean)
        
        if face_count == 0:
            return {"message": "未检测到人脸，请正视摄像头或确保在画面内", "type": "warning", "status": "no_face"}
        elif face_count > 1:
            return {"message": "检测到多个人脸，请保持单人出镜面试", "type": "warning", "status": "multi_face"}
        else:
            return {"message": "正常", "type": "success", "status": "ok"}
            
    except Exception as e:
        logger.error(f"detect_face 发生异常: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/analyze_emotion")
async def analyze_emotion(request: Request):
    try:
        data = await request.json()
        base64_image = data.get("image")
        
        logger.info(f"======== 收到前端图片 ========")
        logger.info(f"图片长度: {len(base64_image) if base64_image else 'None'}")
        
        if not base64_image:
            logger.warning("前端未提供图片数据")
            return JSONResponse(status_code=400, content={"error": "未提供图片数据"})
        
        # 移除 base64 的 data:image/jpeg;base64, 前缀
        if "," in base64_image:
            base64_image_clean = base64_image.split(",")[1]
        else:
            base64_image_clean = base64_image
            
        headers = {
            "Authorization": f"Bearer {DOUBAO_API_KEY}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"使用的 LITE 模型 ID: {DOUBAO_LITE_ENDPOINT_ID}")
        
        payload = {
            "model": DOUBAO_LITE_ENDPOINT_ID,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{base64_image_clean}"
                        },
                        {
                            "type": "input_text",
                            "text": (
                                "作为专业的AI面试监考助理，请严格观察图片中面试者的状态和行为规范。\n"
                                "【重点观察】：1. 眼神是否离开正前方（即离开摄像头或屏幕区域，如看侧边、低头看下方）；2. 是否有走神、迷茫或作弊嫌疑（如眼神飘忽不定，疑似在看屏幕外的提示词或大模型）；3. 情绪是否过度紧张。\n"
                                "【判定尺度】：请保持略高标准的监考严格度。当被试者出现明显的低头（疑似看手机）、脸部侧偏、或者视线明显偏离正前方区域，即立刻判定为违规。允许正常眨眼。\n"
                                "【输出要求】：\n"
                                "1. 如果发现上述违规行为，请立即给出严肃的提醒（例如：'请保持视线在屏幕上，不要看手机或别处' 或 '请注意面试纪律，保持专注'），此时 type 必须为 'warning'。\n"
                                "2. 如果发现过度紧张，给出简短的安抚建议（如：'深呼吸，放松点'），此时 type 为 'warning' 或 'info'。\n"
                                "3. 只有当被试者完全正对镜头且专注时，才给出简短的鼓励（如：'状态不错，继续保持！'），此时 type 为 'success'。\n"
                                "4. 如果没有检测到人脸（例如画面空白、人已离开），请直接返回默认提示：'保持放松，准备面试'，此时 type 必须为 'info'。不需要你发出关于无人脸的警告。\n"
                                "请严格以 JSON 格式返回，包含 'message'（不超过30个字）和 'type'（仅限 'info', 'warning', 'success'）两个字段。"
                            )
                        }
                    ]
                }
            ]
        }
        
        logger.info("准备发起火山引擎 HTTP 请求...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://ark.cn-beijing.volces.com/api/v3/responses",
                    headers=headers,
                    json=payload
                )
            response.raise_for_status()
            response_json = response.json()
            logger.info("HTTP 请求火山引擎成功，开始解析...")
            
            # 解析结果
            try:
                # 兼容不同模型的返回结构
                content = ""
                if "choices" in response_json:
                    content = response_json["choices"][0]["message"]["content"]
                elif "output" in response_json:
                    # doubao-seed 多模态模型的返回结构
                    for item in response_json["output"]:
                        if item.get("type") == "message" and "content" in item:
                            for c in item["content"]:
                                if c.get("type") == "output_text":
                                    content = c.get("text", "")
                                    break
                            
                logger.info(f"[Emotion API] 大模型原始回复: {content}")
                
                if not content:
                    logger.info("[Emotion API] 大模型回复为空，返回默认 success")
                    return {"message": "状态不错，继续保持！", "type": "success"}
                
                content = content.strip()
                if content == "NONE" or content == '"NONE"':
                    logger.info("[Emotion API] 大模型回复了 NONE，返回默认 success")
                    return {"message": "状态不错，继续保持！", "type": "success"}
                    
                # 处理大模型有时可能包裹的 markdown
                if content.startswith("```json"): content = content[7:]
                if content.startswith("```"): content = content[3:]
                if content.endswith("```"): content = content[:-3]
                
                # 尝试将回答解析为 JSON 格式
                result = json.loads(content.strip())
                logger.info(f"[Emotion API] 解析为 JSON 成功: {result}")
                return {
                    "message": result.get("message", "NONE"),
                    "type": result.get("type", "info")
                }
            except json.JSONDecodeError:
                # 如果大模型没有返回 JSON，而是返回了纯文本
                if "NONE" in content.upper() or len(content.strip()) < 2:
                    logger.info(f"[Emotion API] 非 JSON 且含 NONE: {content}")
                    return {"message": "状态不错，继续保持！", "type": "success"}
                else:
                    logger.info(f"[Emotion API] 非 JSON 纯文本回复: {content}")
                    return {"message": content.strip(), "type": "info"}
            except KeyError as e:
                logger.error(f"解析火山引擎返回值失败: {e}, 原始返回值: {response_json}")
                return {"message": "状态不错，继续保持！", "type": "success"}
                
        except Exception as e:
            logger.error(f"请求火山引擎发生异常: {str(e)}")
            return JSONResponse(status_code=500, content={"error": f"请求火山引擎失败: {str(e)}"})
            
    except Exception as e:
        logger.error(f"analyze_emotion 发生未捕获的异常: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})

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
