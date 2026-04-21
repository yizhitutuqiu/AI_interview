import cv2
import numpy as np
import base64
import logging
import os

logger = logging.getLogger("ai_interview.face_detector")

# 初始化 OpenCV 的 Haar 级联人脸检测器
# cv2.data.haarcascades 提供了预训练模型的路径
cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
face_cascade = cv2.CascadeClassifier(cascade_path)

def detect_faces_from_base64(base64_image_str: str) -> int:
    """
    接收 base64 格式的图片字符串，使用 OpenCV Haar Cascade 检测人脸数量
    :param base64_image_str: 不带 'data:image/jpeg;base64,' 前缀的 base64 字符串
    :return: 检测到的人脸数量
    """
    try:
        # 1. 解码 base64 字符串为字节流
        img_bytes = base64.b64decode(base64_image_str)
        
        # 2. 将字节流转换为 numpy 数组
        np_arr = np.frombuffer(img_bytes, np.uint8)
        
        # 3. 使用 OpenCV 解码为图像 (BGR 格式)
        img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img_bgr is None:
            logger.warning("[FaceDetector] 图像解码失败")
            return 0
            
        # 4. Haar Cascade 通常在灰度图上运行更快且更准确
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # 5. 进行人脸检测
        # scaleFactor: 每次图像尺寸减小的比例
        # minNeighbors: 每个候选矩形必须保留的邻居数量，越高越严格
        # minSize: 检测的最小面部大小
        faces = face_cascade.detectMultiScale(
            img_gray, 
            scaleFactor=1.1, 
            minNeighbors=4, 
            minSize=(30, 30)
        )
        
        face_count = len(faces)
        logger.info(f"[FaceDetector] 检测到 {face_count} 张人脸")
        
        return face_count
        
    except Exception as e:
        logger.error(f"[FaceDetector] 人脸检测过程发生异常: {str(e)}")
        # 发生异常时，为了不阻塞后续的大模型流程，默认返回 1
        return 1

