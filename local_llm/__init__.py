"""
简历智能评估系统 - 本地大模型模块

该模块提供本地大模型调用能力，支持GPU加速推理。

核心功能：
1. GPU检测：检测电脑是否有可用的GPU
2. 模型加载：优先从本地路径加载，本地不存在时自动从HuggingFace下载
3. 模型推理：使用本地模型进行推理
4. 设备管理：自动选择GPU或CPU
"""

from .local_model import detect_gpu, get_device, call_local_model, LocalModel, get_local_model