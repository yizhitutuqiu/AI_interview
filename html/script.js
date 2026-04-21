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

    // 面试场景状态
    let currentCompanyType = '';
    let currentJobRole = '';
    let currentThinkTime = 15;
    let currentAnswerTime = 60;

    // 存储对话历史
    let messageHistory = [];

    // 定时器相关变量
    let timerInterval = null;
    let currentTimerType = 'none'; // 'none', 'think', 'answer'
    const timerContainer = document.getElementById('timer-container');
    const timerProgress = document.getElementById('timer-progress');
    const timerLabel = document.getElementById('timer-label');
    const timerValue = document.getElementById('timer-value');

    // ================== 1. 初始化设置界面 ==================
    startBtn.addEventListener('click', () => {
        currentCompanyType = document.getElementById('company-type').value;
        currentJobRole = document.getElementById('job-role').value;
        currentThinkTime = parseInt(document.getElementById('think-time').value, 10);
        currentAnswerTime = parseInt(document.getElementById('answer-time').value, 10);
        
        scenarioInfo.textContent = `面试公司: ${currentCompanyType} | 岗位: ${currentJobRole}`;
        
        // 隐藏设置界面，显示聊天界面
        setupScreen.classList.add('hidden');
        chatScreen.classList.remove('hidden');

        // 初始化 AI 第一句话
        const initialMsg = `您好！我是您的AI面试官。欢迎您来面试【${currentCompanyType}】的【${currentJobRole}】岗位。今天我们将进行一场专业面试，您准备好了吗？如果准备好了，请简单做个自我介绍吧。`;
        
        showAiBubble(initialMsg, false); // 初始消息直接显示，不需要动画流式
        messageHistory.push({ role: 'assistant', content: initialMsg });
        
        // 开启第一轮回答倒计时
        startTimer('answer', currentAnswerTime);
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

    textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
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
                    messages: messageHistory 
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                showAiBubble(`⚠️ 发生错误: ${errData.error || '未知错误'}`);
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

            // AI 提问完毕，自动开启用户的“思考时间”倒计时
            startTimer('think', currentThinkTime);

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
                    messages: messageHistory 
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
});
