document.addEventListener('DOMContentLoaded', () => {
    const setupScreen = document.getElementById('setup-screen');
    const chatScreen = document.getElementById('chat-screen');
    const startBtn = document.getElementById('start-btn');
    const scenarioInfo = document.getElementById('scenario-info');
    
    // 新版 UI 元素
    const aiBubbleContainer = document.getElementById('ai-bubble-container');
    const aiBubbleContent = document.getElementById('ai-bubble-content');
    const siriContainer = document.getElementById('siri-container');
    const userReplyPreview = document.getElementById('user-reply-preview');

    const textInput = document.getElementById('text-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');
    const voiceStatus = document.getElementById('voice-status');
    const endInterviewBtn = document.getElementById('end-interview-btn');

    // 报告界面元素
    const reportScreen = document.getElementById('report-screen');
    const reportContent = document.getElementById('report-content');
    const reportLoading = document.getElementById('report-loading');
    const finalScoreEl = document.getElementById('final-score');
    const overallCommentEl = document.getElementById('overall-comment');
    const strengthsList = document.getElementById('strengths-list');
    const weaknessesList = document.getElementById('weaknesses-list');
    const restartBtn = document.getElementById('restart-btn');

    // 视频与 AI 助理元素
    const userVideo = document.getElementById('user-video');
    const snapshotCanvas = document.getElementById('snapshot-canvas');
    const assistantSidebar = document.getElementById('ai-assistant-sidebar');
    const assistantContent = document.getElementById('assistant-content');
    const assistantAvatar = document.getElementById('assistant-avatar');
    const avatarFace = document.getElementById('avatar-face');
    const assistantStatusText = document.getElementById('assistant-status-text');

    let videoStream = null;
    let emotionAnalysisTimer = null;
    let currentAnalysisInterval = 12000; // 默认 12 秒请求一次
    let isAnalyzing = false; // 防止请求并发堆叠

    // 面试场景状态
    let currentCompanyType = '';
    let currentJobRole = '';
    let currentThinkTime = 15;
    let currentAnswerTime = 60;

    // 存储对话历史
    let messageHistory = [];
    // 存储 AI 助理观察记录
    let assistantObservations = [];

    // 定时器相关变量
    let timerInterval = null;
    let currentTimerType = 'none'; // 'none', 'think', 'answer'
    const timerContainer = document.getElementById('timer-container');
    const timerProgress = document.getElementById('timer-progress');
    const timerLabel = document.getElementById('timer-label');
    const timerValue = document.getElementById('timer-value');

    // ================== 1. 初始化设置界面 ==================
    startBtn.addEventListener('click', async () => {
        currentCompanyType = document.getElementById('company-type').value;
        currentJobRole = document.getElementById('job-role').value;
        currentThinkTime = parseInt(document.getElementById('think-time').value, 10);
        currentAnswerTime = parseInt(document.getElementById('answer-time').value, 10);
        
        scenarioInfo.textContent = `面试公司: ${currentCompanyType} | 岗位: ${currentJobRole}`;
        
        // 尝试获取摄像头权限并开启视频流
        try {
            videoStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            userVideo.srcObject = videoStream;
            console.log("[系统] 摄像头初始化成功");
            
            // 当视频元数据加载完毕后再启动 AI 助理定时器，确保 videoWidth 有值
            userVideo.onloadedmetadata = () => {
                console.log(`[系统] 视频加载完毕，分辨率: ${userVideo.videoWidth}x${userVideo.videoHeight}`);
            };
        } catch (err) {
            console.error("无法获取摄像头权限:", err);
            addAssistantMessage("无法访问您的摄像头，情绪分析已关闭。请在浏览器中允许权限。", "warning");
        }

        // 隐藏设置界面，显示聊天界面和 AI 助理边栏
        setupScreen.classList.add('hidden');
        chatScreen.classList.remove('hidden');
        assistantSidebar.classList.remove('hidden');

        // 初始化 AI 第一句话
        const initialMsg = `您好！我是您的AI面试官。欢迎您来面试【${currentCompanyType}】的【${currentJobRole}】岗位。今天我们将进行一场专业面试，您准备好了吗？如果准备好了，请简单做个自我介绍吧。`;
        
        showAiBubble(initialMsg, false); // 初始消息直接显示，不需要动画流式
        messageHistory.push({ role: 'assistant', content: initialMsg });
        assistantObservations = []; // 初始化清空观察记录
        
        // 开启第一轮回答倒计时
        startTimer('answer', currentAnswerTime);

        // 开启情绪分析定时任务 (每 5 秒一次)
        if (videoStream) {
            startEmotionAnalysis();
        }
    });

    // ================== 1.5 倒计时逻辑 ==================
    function startTimer(type, totalSeconds) {
        stopTimer();
        currentTimerType = type;
        let remainingSeconds = totalSeconds;
        
        timerContainer.classList.remove('hidden');
        timerLabel.textContent = type === 'think' ? '思考' : '回答';
        timerProgress.classList.remove('warning');
        
        // 初始化显示
        updateTimerUI(remainingSeconds, totalSeconds);

        timerInterval = setInterval(() => {
            remainingSeconds--;
            
            updateTimerUI(remainingSeconds, totalSeconds);

            if (remainingSeconds <= 0) {
                stopTimer();
                handleTimeout(type);
            }
        }, 1000);
    }

    function updateTimerUI(remaining, total) {
        timerValue.textContent = remaining;
        
        // 更新 SVG 进度条 (周长约 283)
        const dashoffset = 283 - (remaining / total) * 283;
        timerProgress.style.strokeDashoffset = dashoffset;

        // 如果剩下不到 1/4 的时间，标红警告
        if (remaining <= total * 0.25) {
            timerProgress.classList.add('warning');
        } else {
            timerProgress.classList.remove('warning');
        }
    }

    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
        currentTimerType = 'none';
        timerContainer.classList.add('hidden');
    }

    function handleTimeout(type) {
        if (type === 'think') {
            // 思考时间结束，自动转入回答时间
            startTimer('answer', currentAnswerTime);
            showUserPreview("（思考时间结束，请作答）");
        } else if (type === 'answer') {
            // 回答时间结束，自动交卷发送
            const text = textInput.value.trim();
            if (text) {
                sendMessage();
            } else {
                // 如果没输入内容就超时，发送默认超时提示
                textInput.value = "（抱歉，我未能按时作答）";
                sendMessage();
            }
        }
    }


    // ================== 2. 语音识别逻辑 (Web Speech API) ==================
    let recognition = null;
    let isRecording = false;

    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'zh-CN';

        recognition.onstart = () => {
            isRecording = true;
            micBtn.classList.add('recording');
            voiceStatus.classList.remove('hidden');
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }
            
            textInput.value = (textInput.dataset.originalText || '') + finalTranscript + interimTranscript;
            autoResizeTextarea();
        };

        recognition.onerror = (event) => {
            console.error('语音识别错误:', event.error);
            stopRecording();
        };

        recognition.onend = () => {
            if (isRecording) {
                stopRecording();
            }
        };
    } else {
        micBtn.style.display = 'none';
        console.warn('您的浏览器不支持 Web Speech API');
    }

    function toggleRecording() {
        if (!recognition) return;
        if (isRecording) {
            stopRecording();
        } else {
            textInput.dataset.originalText = textInput.value;
            recognition.start();
        }
    }

    function stopRecording() {
        if (recognition) {
            recognition.stop();
        }
        isRecording = false;
        micBtn.classList.remove('recording');
        voiceStatus.classList.add('hidden');
        textInput.dataset.originalText = '';
    }

    micBtn.addEventListener('click', toggleRecording);

    // ================== 3. 输入框逻辑 ==================
    function autoResizeTextarea() {
        textInput.style.height = 'auto';
        textInput.style.height = (textInput.scrollHeight) + 'px';
    }

    textInput.addEventListener('input', autoResizeTextarea);

    let lastEnterTime = 0;
    textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            if (e.repeat) return; // 忽略长按
            const currentTime = new Date().getTime();
            if (currentTime - lastEnterTime < 500) {
                e.preventDefault();
                // 移除因为第一次 Enter 产生的换行符
                textInput.value = textInput.value.replace(/\n$/, '');
                sendMessage();
                lastEnterTime = 0;
            } else {
                lastEnterTime = currentTime;
            }
        }
    });

    sendBtn.addEventListener('click', sendMessage);


    // ================== 4. 显示控制 ==================
    function showAiBubble(text, isTyping = false) {
        aiBubbleContainer.classList.remove('hidden');
        if (isTyping) {
            aiBubbleContent.innerHTML = `<div class="typing-indicator"><span></span><span></span><span></span></div>`;
        } else {
            aiBubbleContent.textContent = text;
        }
        // 自动滚动到气泡底部
        aiBubbleContent.scrollTop = aiBubbleContent.scrollHeight;
    }

    function hideAiBubble() {
        aiBubbleContainer.classList.add('hidden');
    }

    function showUserPreview(text) {
        userReplyPreview.textContent = text;
        userReplyPreview.classList.add('visible');
        
        // 3秒后自动隐藏用户的预览气泡
        setTimeout(() => {
            userReplyPreview.classList.remove('visible');
        }, 3000);
    }


    // ================== 5. 发送与流式接收逻辑 ==================
    async function sendMessage() {
        const text = textInput.value.trim();
        if (!text) return;

        if (isRecording) {
            stopRecording();
        }

        // 发送消息时停止定时器
        stopTimer();

        // 显示用户的回复预览
        showUserPreview(text);
        messageHistory.push({ role: 'user', content: text });

        // 清空输入框并重置高度
        textInput.value = '';
        textInput.style.height = 'auto';
        sendBtn.disabled = true;

        // 开启 Siri 动画和 Loading 气泡
        siriContainer.classList.add('speaking');
        showAiBubble('', true);
        
        let aiReply = '';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    company_type: currentCompanyType,
                    job_role: currentJobRole,
                    think_time: currentThinkTime,
                    answer_time: currentAnswerTime,
                    messages: messageHistory,
                    assistant_observations: assistantObservations
                })
            });

            if (!response.ok) {
                // 读取原始文本，防止不是 json
                const errText = await response.text();
                let errMsg = '未知错误';
                try {
                    const errData = JSON.parse(errText);
                    errMsg = errData.error || errText;
                } catch(e) {
                    errMsg = errText;
                }
                showAiBubble(`⚠️ 发生错误: ${errMsg}`);
                siriContainer.classList.remove('speaking');
                sendBtn.disabled = false;
                return;
            }

            // 处理 SSE 流式响应
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';
            
            // 清空 loading，准备接收文字
            aiBubbleContent.textContent = '';
            let isFinished = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                let newlineIdx;
                
                while ((newlineIdx = buffer.indexOf('\n\n')) >= 0) {
                    const eventStr = buffer.slice(0, newlineIdx);
                    buffer = buffer.slice(newlineIdx + 2);
                    
                    const lines = eventStr.split('\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const dataStr = line.slice(6).trim();
                            if (dataStr === '[DONE]') continue;
                            
                            try {
                                const dataObj = JSON.parse(dataStr);
                                if (dataObj.error) {
                                    aiReply += `\n[Error: ${dataObj.error}]`;
                                } else if (dataObj.text) {
                                    if (dataObj.text.includes('[INTERVIEW_FINISHED]')) {
                                        dataObj.text = dataObj.text.replace('[INTERVIEW_FINISHED]', '');
                                        isFinished = true;
                                    }
                                    aiReply += dataObj.text;
                                    // 实时更新气泡内容
                                    aiBubbleContent.textContent = aiReply;
                                    aiBubbleContent.scrollTop = aiBubbleContent.scrollHeight;
                                }
                            } catch (e) {
                                console.error('Parse error:', e, dataStr);
                            }
                        }
                    }
                }
            }

            messageHistory.push({ role: 'assistant', content: aiReply });

            if (isFinished) {
                // 触发结束面试流程
                setTimeout(() => {
                    endInterviewBtn.click();
                }, 2000); // 延迟2秒让用户看完最后一句话
            } else {
                // AI 提问完毕，自动开启用户的“思考时间”倒计时
                startTimer('think', currentThinkTime);
            }

        } catch (error) {
            showAiBubble(`⚠️ 网络错误: ${error.message}`);
        } finally {
            // 停止 Siri 动画
            siriContainer.classList.remove('speaking');
            sendBtn.disabled = false;
            textInput.focus();
        }
    }

    // ================== 6. 面试报告与图表渲染 ==================
    endInterviewBtn.addEventListener('click', async () => {
        // 确认是否结束面试
        if (!confirm('确定要结束面试并生成评估报告吗？')) return;

        stopTimer();
        if (isRecording) stopRecording();
        stopEmotionAnalysis();
        
        chatScreen.classList.add('hidden');
        reportScreen.classList.remove('hidden');
        
        try {
            const response = await fetch('/api/report', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    company_type: currentCompanyType,
                    job_role: currentJobRole,
                    think_time: currentThinkTime,
                    answer_time: currentAnswerTime,
                    messages: messageHistory,
                    assistant_observations: assistantObservations
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                alert(`生成报告失败: ${errData.error}`);
                reportScreen.classList.add('hidden');
                chatScreen.classList.remove('hidden');
                return;
            }

            const reportData = await response.json();
            
            // 渲染数据
            reportLoading.classList.add('hidden');
            reportContent.classList.remove('hidden');
            
            finalScoreEl.textContent = reportData.total_score;
            overallCommentEl.textContent = reportData.overall_comment;
            
            strengthsList.innerHTML = reportData.strengths.map(s => `<li>${s}</li>`).join('');
            weaknessesList.innerHTML = reportData.weaknesses.map(w => `<li>${w}</li>`).join('');
            
            // 渲染雷达图
            renderRadarChart(reportData.dimensions);

        } catch (error) {
            alert(`网络错误: ${error.message}`);
            reportScreen.classList.add('hidden');
            chatScreen.classList.remove('hidden');
        }
    });

    function renderRadarChart(dimensions) {
        const chartDom = document.getElementById('radar-chart');
        const myChart = echarts.init(chartDom);
        
        const option = {
            tooltip: {},
            radar: {
                indicator: [
                    { name: '专业技能', max: 100 },
                    { name: '沟通表达', max: 100 },
                    { name: '逻辑思维', max: 100 },
                    { name: '应变/抗压', max: 100 },
                    { name: '文化匹配度', max: 100 }
                ],
                axisName: {
                    color: '#cbd5e1',
                    fontSize: 14
                },
                splitArea: {
                    areaStyle: {
                        color: ['rgba(37, 99, 235, 0.1)', 'rgba(37, 99, 235, 0.2)', 'rgba(37, 99, 235, 0.4)', 'rgba(37, 99, 235, 0.6)', 'rgba(37, 99, 235, 0.8)'].reverse()
                    }
                },
                axisLine: {
                    lineStyle: {
                        color: 'rgba(255, 255, 255, 0.2)'
                    }
                },
                splitLine: {
                    lineStyle: {
                        color: 'rgba(255, 255, 255, 0.2)'
                    }
                }
            },
            series: [{
                name: '能力评估',
                type: 'radar',
                data: [
                    {
                        value: [
                            dimensions.professional || 0, 
                            dimensions.communication || 0, 
                            dimensions.logic || 0, 
                            dimensions.adaptability || 0, 
                            dimensions.culture_fit || 0
                        ],
                        name: '综合评分',
                        itemStyle: { color: '#8b5cf6' },
                        areaStyle: { color: 'rgba(139, 92, 246, 0.4)' },
                        label: {
                            show: true,
                            color: '#fff'
                        }
                    }
                ]
            }]
        };

        myChart.setOption(option);
        
        // 监听窗口大小改变，重绘图表
        window.addEventListener('resize', () => {
            myChart.resize();
        });
    }

    restartBtn.addEventListener('click', () => {
        window.location.reload();
    });

    // ================== 7. AI 助理视频分析与状态提示 ==================
    let faceDetectionTimer = null;
    let isDetectingFace = false;
    
    // 保存上一次 AI 助理情感分析的提示状态
    let lastEmotionMessage = "正在分析您的状态，随时为您提供鼓励和建议...";
    let lastEmotionType = "info";
    // 保存当前 UI 上实际显示的最后一条文本，用于防止重复弹窗
    let lastDisplayedMessage = "";
    // 标记当前是否正处于“人脸检测异常”的警告状态
    let isFaceWarningActive = false;

    function startEmotionAnalysis() {
        // 延迟 3 秒让摄像头充分初始化，然后启动循环
        emotionAnalysisTimer = setTimeout(scheduleNextAnalysis, 3000);
        // 启动高频人脸检测定时器，每 500ms (一秒两次) 执行一次
        faceDetectionTimer = setInterval(captureAndDetectFace, 500);
    }

    function stopEmotionAnalysis() {
        if (emotionAnalysisTimer) {
            clearTimeout(emotionAnalysisTimer);
            emotionAnalysisTimer = null;
        }
        if (faceDetectionTimer) {
            clearInterval(faceDetectionTimer);
            faceDetectionTimer = null;
        }
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
            videoStream = null;
        }
    }

    async function captureAndDetectFace() {
        if (!videoStream || !userVideo.videoWidth || isDetectingFace) return;
        isDetectingFace = true;
        try {
            const targetWidth = 320;
            const scale = targetWidth / userVideo.videoWidth;
            const targetHeight = userVideo.videoHeight * scale;

            // 使用独立离屏 Canvas 防止和情感分析冲突
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = targetWidth;
            tempCanvas.height = targetHeight;
            const ctx = tempCanvas.getContext('2d');
            ctx.drawImage(userVideo, 0, 0, targetWidth, targetHeight);
            
            const base64Image = tempCanvas.toDataURL('image/jpeg', 0.6);

            const response = await fetch('/api/detect_face', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: base64Image })
            });

            if (response.ok) {
                const data = await response.json();
                // 只有在检测到异常时才更新 UI 提示，正常情况下不覆盖情感分析的提示
                if (data.type === 'warning') {
                    isFaceWarningActive = true;
                    // 这里传入 data.status ('no_face' 或 'multi_face') 作为特殊提示类型
                    addAssistantMessage(data.message, data.status || data.type);
                } else if (data.type === 'success' && isFaceWarningActive) {
                    // 如果当前没有异常，且之前处于警告状态，则恢复为上次情感分析的提示
                    isFaceWarningActive = false;
                    addAssistantMessage(lastEmotionMessage, lastEmotionType);
                }
            }
        } catch (error) {
            console.error("[AI 助理] 人脸检测异常:", error);
        } finally {
            isDetectingFace = false;
        }
    }

    function scheduleNextAnalysis() {
        // 防止上一次请求还没回来，就发起了下一次
        if (!isAnalyzing) {
            // 这里不使用 await，让 captureAndAnalyze 异步（后台）去执行，不阻塞当前的定时器调度
            captureAndAnalyze().catch(console.error);
        }
        
        // 无论上一次是否还在 analyzing，定时器都会继续排队下一次。
        // 如果下一次触发时仍在 analyzing，就会跳过当次抓拍。
        emotionAnalysisTimer = setTimeout(scheduleNextAnalysis, currentAnalysisInterval);
    }

    async function captureAndAnalyze() {
        console.log("[AI 助理] 尝试截图并分析...");
        if (!videoStream) {
            console.warn("[AI 助理] 摄像头视频流未就绪");
            return;
        }
        if (!userVideo.videoWidth) {
            console.warn("[AI 助理] videoWidth 为 0，可能视频未加载");
            return;
        }
        if (isAnalyzing) {
            console.warn("[AI 助理] 正在分析中，跳过本次");
            return;
        }

        isAnalyzing = true;

        try {
            // 将图片压缩到更小的分辨率以降低传输和推理时间 (宽度设为 320)
            const targetWidth = 320;
            const scale = targetWidth / userVideo.videoWidth;
            const targetHeight = userVideo.videoHeight * scale;

            snapshotCanvas.width = targetWidth;
            snapshotCanvas.height = targetHeight;
            
            const ctx = snapshotCanvas.getContext('2d');
            ctx.drawImage(userVideo, 0, 0, targetWidth, targetHeight);
            
            // 使用 JPEG 格式并进一步压缩质量到 0.6
            const base64Image = snapshotCanvas.toDataURL('image/jpeg', 0.6);
            console.log(`[AI 助理] 截图成功，Base64 长度: ${base64Image.length}`);

            const response = await fetch('/api/analyze_emotion', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: base64Image })
            });

            if (!response.ok) {
                console.warn(`[AI 助理] 分析请求失败: HTTP ${response.status}`);
                currentAnalysisInterval = 25000;
            } else {
                const data = await response.json();
                console.log("[AI 助理] 接收到后端数据:", data);
                currentAnalysisInterval = 12000;
                
                // 去掉了对 "NONE" 的强行拦截，因为后端已经保证不会返回 NONE 了
                if (data.message) {
                    // 更新最后一次的情感状态
                    lastEmotionMessage = data.message;
                    lastEmotionType = data.type || "info";
                    
                    // 仅当没有本地人脸警告时，才更新 UI
                    if (!isFaceWarningActive) {
                        addAssistantMessage(lastEmotionMessage, lastEmotionType);
                    }
                    
                    // 记录观察信息，带上时间戳
                    const now = new Date();
                    const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
                    assistantObservations.push(`[${timeStr}] ${data.message}`);
                }
            }
        } catch (error) {
            console.error("[AI 助理] 截屏分析异常:", error);
            // 异常降频
            currentAnalysisInterval = 5000;
        } finally {
            isAnalyzing = false;
        }
    }

    function addAssistantMessage(text, type = 'info') {
        // 防止相同的提示内容重复弹窗导致视觉干扰
        if (text === lastDisplayedMessage) {
            return;
        }
        lastDisplayedMessage = text;

        // 覆盖模式：清空之前的所有内容，只显示最新的一条提示
        assistantContent.innerHTML = '';
        
        // 由于特殊类型也属于 warning，消息气泡样式统一为 warning，但图标独立
        let cssType = type;
        if (type === 'no_face' || type === 'multi_face') {
            cssType = 'warning';
        }
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `assistant-msg ${cssType}`;
        msgDiv.textContent = text;
        
        // 添加一个微小的时间戳让用户知道它更新了
        const timeSpan = document.createElement('span');
        timeSpan.style.display = 'block';
        timeSpan.style.fontSize = '0.75rem';
        timeSpan.style.color = 'rgba(255,255,255,0.4)';
        timeSpan.style.marginTop = '6px';
        const now = new Date();
        timeSpan.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
        msgDiv.appendChild(timeSpan);
        
        assistantContent.appendChild(msgDiv);
        
        // =============== 同步更新中心视觉实体的状态 ===============
        assistantAvatar.className = `assistant-avatar ${cssType}`;
        
        // 根据状态类型改变图标
        if (type === 'no_face') {
            avatarFace.innerHTML = '<i class="fa-solid fa-question"></i>';
            avatarFace.style.color = '#ffffff'; // 白色问号
            assistantStatusText.textContent = "人去哪了？";
            assistantStatusText.style.color = "#e2e8f0";
        } else if (type === 'multi_face') {
            avatarFace.innerHTML = '<i class="fa-solid fa-users"></i>';
            avatarFace.style.color = '#ef4444'; // 红色多人
            assistantStatusText.textContent = "检测到多个人脸！";
            assistantStatusText.style.color = "#fca5a5";
        } else if (type === 'warning') {
            avatarFace.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
            avatarFace.style.color = ''; // 恢复默认
            assistantStatusText.textContent = "请注意状态";
            assistantStatusText.style.color = "#fca5a5";
        } else if (type === 'success') {
            avatarFace.innerHTML = '<i class="fa-regular fa-face-laugh-beam"></i>';
            avatarFace.style.color = ''; // 恢复默认
            assistantStatusText.textContent = "状态极佳！";
            assistantStatusText.style.color = "#86efac";
        } else {
            avatarFace.innerHTML = '<i class="fa-regular fa-face-smile"></i>';
            avatarFace.style.color = ''; // 恢复默认
            assistantStatusText.textContent = "保持放松，准备面试";
            assistantStatusText.style.color = "#93c5fd";
        }
    }

});
