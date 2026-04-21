import cv2
import numpy as np
import base64
import logging
import os
import yaml

logger = logging.getLogger("ai_interview.face_detector")

# 读取配置文件
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'configs', 'config.yaml')
detector_type = "haar"  # 默认使用 haar

if os.path.exists(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config and 'face_detector' in config:
                detector_type = config['face_detector'].lower()
                logger.info(f"[FaceDetector] 配置文件指定使用检测器: {detector_type}")
    except Exception as e:
        logger.error(f"[FaceDetector] 读取配置文件失败: {e}")

# 全局变量，用于懒加载检测器
face_cascade = None
mtcnn_detector = None

def get_haar_detector():
    global face_cascade
    if face_cascade is None:
        cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
        face_cascade = cv2.CascadeClassifier(cascade_path)
        logger.info("[FaceDetector] Haar Cascade 模型加载成功")
    return face_cascade

def get_mtcnn_detector():
    global mtcnn_detector
    if mtcnn_detector is None:
        try:
            from mtcnn import MTCNN
            # 将 TensorFlow 的日志级别调高，减少控制台垃圾信息
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 
            mtcnn_detector = MTCNN()
            logger.info("[FaceDetector] MTCNN 模型加载成功")
        except ImportError as e:
            logger.error(f"[FaceDetector] 导入 MTCNN 失败，请确保已安装 mtcnn 和 tensorflow: {e}")
            logger.info("[FaceDetector] 回退到 Haar Cascade 检测器")
            return None
    return mtcnn_detector

def detect_faces_from_base64(base64_image_str: str) -> int:
    """
    接收 base64 格式的图片字符串，根据配置使用对应的算法检测人脸数量
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
            
        # 根据配置选择检测器
        if detector_type == "mtcnn":
            detector = get_mtcnn_detector()
            if detector is not None:
                # MTCNN 需要 RGB 格式的图片
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                faces = detector.detect_faces(img_rgb)
                
                # 过滤掉置信度过低的结果
                valid_faces = [f for f in faces if f.get('confidence', 0) > 0.85]
                face_count = len(valid_faces)
                # logger.debug(f"[FaceDetector-MTCNN] 检测到 {face_count} 张人脸")
                return face_count
            else:
                # 如果 MTCNN 加载失败，自动回退到 Haar
                pass

        # 回退或默认使用 Haar Cascade
        detector = get_haar_detector()
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # scaleFactor: 每次图像尺寸减小的比例
        # minNeighbors: 每个候选矩形必须保留的邻居数量，越高越严格
        # minSize: 检测的最小面部大小
        faces = detector.detectMultiScale(
            img_gray, 
            scaleFactor=1.1, 
            minNeighbors=4, 
            minSize=(30, 30)
        )
        
        face_count = len(faces)
        # logger.debug(f"[FaceDetector-Haar] 检测到 {face_count} 张人脸")
        
        return face_count
        
    except Exception as e:
        logger.error(f"[FaceDetector] 人脸检测过程发生异常: {str(e)}")
        # 发生异常时，为了不阻塞后续的大模型流程，默认返回 1
        return 1

