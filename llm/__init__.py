"""
简历智能评估系统 - 远程大模型模块

该模块提供远程大模型API调用能力，支持阿里云百炼等大模型服务。

核心功能：
1. API调用：调用远程大模型API进行评估
2. Prompt构建：构建评估所需的Prompt
3. 响应解析：解析大模型返回的结果
"""

from .remote_llm import call_llm_api, parse_llm_response, build_evaluation_prompt
