"""
简历智能评估系统 - 远程大模型API调用模块

该模块负责调用远程大模型API进行评估，支持阿里云百炼等大模型服务。

核心功能：
1. Prompt构建：将评估标准和候选人信息组合成大模型可理解的Prompt
2. API调用：调用大模型API进行评估
3. 响应解析：解析大模型返回的JSON结果

使用依赖：
- requests：HTTP请求，调用大模型API
- json：JSON数据处理
- re：正则表达式匹配
- time：时间控制（请求间隔）
- logging：日志记录
"""

import os
import re
import json
import logging
import requests
import time
from config import LLM_CONFIG, PRIORITY_LEVELS
from utils.evaluation_parser import get_evaluation_criteria, format_evaluation_criteria
from utils.prompt_templates import build_candidate_info_text, EVALUATION_INSTRUCTION, LOCAL_EVALUATION_INSTRUCTION, EVALUATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def build_evaluation_prompt(candidate, position_key, use_local=False):
    """
    构建评估Prompt，包含候选人信息和评估标准
    
    Prompt结构：
    1. 评估标准：格式化后的岗位评估维度和优先级等级（含达标标准子项）
    2. 动态权重计算规则：说明如何根据达标标准中的项目数量计算分数
    3. 候选人信息：姓名、岗位、经验、学历、技能、项目经验、个人简介、完整文本
    4. 评估指令：要求大模型按照JSON格式输出评估结果，包含新字段
    
    Args:
        candidate: 候选人信息字典
        position_key: 岗位类型关键字
        use_local: 是否使用本地模型（本地模型使用简化版提示词）
        
    Returns:
        str: 构建好的Prompt文本
    """
    criteria_text = format_evaluation_criteria(position_key)
    
    criteria = get_evaluation_criteria(position_key)
    
    dynamic_weight_text = "\n【动态权重计算规则】\n"
    dynamic_weight_text += "每个评估维度的权重将按照其达标标准中的项目数量进行动态分配：\n"
    for dim in criteria['dimensions']:
        if dim.get('item_count', 0) > 0:
            per_item_score = dim['weight'] / dim['item_count']
            dynamic_weight_text += f"  {dim['id']}. {dim['name']}（权重{dim['weight']}%）：{dim['item_count']}个达标项，每项{per_item_score:.1f}%\n"
            for i, item in enumerate(dim.get('standard_items', []), 1):
                dynamic_weight_text += f"    {i}. {item}\n"
    
    candidate_info = build_candidate_info_text(candidate)
    
    instruction = LOCAL_EVALUATION_INSTRUCTION if use_local else EVALUATION_INSTRUCTION
    
    prompt = criteria_text + dynamic_weight_text + "\n" + candidate_info + "\n" + instruction
    
    return prompt


def call_llm_api(prompt, config=None):
    """
    调用大模型API进行评估
    
    使用OpenAI兼容的Chat Completions API格式调用大模型。
    如果API配置不完整（缺少api_base或api_key），则返回None。
    支持自动重试机制，当调用失败时最多重试3次，采用指数退避策略。
    
    Args:
        prompt: Prompt文本
        config: API配置（可选，默认使用LLM_CONFIG）
        
    Returns:
        str: 大模型返回的响应文本，若调用失败返回None
    """
    if config is None:
        config = LLM_CONFIG
    
    api_base = config.get('api_base', '')
    api_key = config.get('api_key', '')
    
    if not api_base or not api_key:
        logger.warning("大模型API配置不完整，使用本地规则评估")
        return None
    
    max_retries = config.get('max_retries', 3)
    timeout_connect = config.get('timeout_connect', 15)
    timeout_read = config.get('timeout_read', 120)
    timeout = (timeout_connect, timeout_read)
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    system_prompt = config.get('system_prompt', EVALUATION_SYSTEM_PROMPT)
    
    payload = {
        'model': config.get('model') or 'qwen-max',
        'messages': [
            {
                'role': 'system',
                'content': system_prompt
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'temperature': config.get('temperature', 0.1),
        'max_tokens': config.get('max_tokens', 2000)
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f'{api_base}/chat/completions',
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            response.raise_for_status()
            
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            
            return None
        
        except requests.exceptions.Timeout:
            logger.warning(f"调用大模型API超时，第{attempt+1}/{max_retries}次尝试")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            else:
                logger.error(f"调用大模型API超时，已达最大重试次数{max_retries}")
                return None
        
        except Exception as e:
            logger.warning(f"调用大模型API失败，第{attempt+1}/{max_retries}次尝试，错误: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            else:
                logger.error(f"调用大模型API失败，已达最大重试次数{max_retries}: {str(e)}")
                return None


def parse_llm_response(response_text):
    """
    解析大模型返回结果，提取评估信息
    
    支持多种解析方式：
    1. JSON解析：从响应中提取JSON格式的评估结果
    2. 正则解析：当JSON解析失败时，使用正则表达式提取关键信息
    
    预处理：
    - 去除markdown代码块标记（```json ... ```）
    - 去除思维链标签
    - 去除其他常见噪声
    
    Args:
        response_text: 大模型返回的文本
        
    Returns:
        dict: 包含评估结果的字典，若无法提取有效分数返回None
    """
    if not response_text:
        return None
    
    cleaned_text = response_text.strip()
    
    cleaned_text = re.sub(r'<think>[\s\S]*?</think>', '', cleaned_text)
    
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned_text)
    if code_block_match:
        cleaned_text = code_block_match.group(1).strip()
    
    result = {
        'match_score': 0,
        'priority': 'P3',
        'phone': '',
        'gender': '',
        'age': '',
        'education': '',
        'core_strengths': '',
        'main_risks': '',
        'suggested_action': '',
        'rating_reason': '',
        'intention_modules': '',
        'preliminary_info': '',
        'dimension_scores': {},
        'dimension_details': {}
    }
    
    try:
        json_match = re.search(r'\{[\s\S]*\}', cleaned_text)
        if json_match:
            json_str = json_match.group(0)
            try:
                data = json.loads(json_str)
                
                if 'match_score' in data:
                    result['match_score'] = int(data['match_score'])
                
                if 'priority' in data:
                    result['priority'] = data['priority']
                
                if 'phone' in data:
                    result['phone'] = str(data['phone'])
                
                if 'gender' in data:
                    result['gender'] = data['gender']
                
                if 'age' in data:
                    result['age'] = str(data['age'])
                
                if 'education' in data:
                    result['education'] = data['education']
                
                if 'core_strengths' in data:
                    result['core_strengths'] = data['core_strengths']
                
                if 'main_risks' in data:
                    result['main_risks'] = data['main_risks']
                
                if 'suggested_action' in data:
                    result['suggested_action'] = data['suggested_action']
                
                if 'rating_reason' in data:
                    result['rating_reason'] = data['rating_reason']
                
                if 'intention_modules' in data:
                    result['intention_modules'] = data['intention_modules']
                
                if 'preliminary_info' in data:
                    result['preliminary_info'] = data['preliminary_info']
                
                if 'dimension_scores' in data:
                    result['dimension_scores'] = data['dimension_scores']
                
                if 'dimension_details' in data:
                    result['dimension_details'] = data['dimension_details']
                
                if result['match_score'] > 0:
                    return result
                
                logger.warning(f"JSON解析成功但match_score为0，响应前200字: {cleaned_text[:200]}")
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败: {e}，尝试正则提取")
        
        score_match = re.search(r'匹配度[\s：:]*(\d+)%', cleaned_text)
        if not score_match:
            score_match = re.search(r'match_score[\s：:]*["\']?(\d+)', cleaned_text)
        if score_match:
            result['match_score'] = int(score_match.group(1))
        
        priority_match = re.search(r'优先级[\s：:]*([Pp][0-3])', cleaned_text)
        if not priority_match:
            priority_match = re.search(r'priority[\s：:]*["\']?([Pp][0-3])', cleaned_text)
        if priority_match:
            result['priority'] = priority_match.group(1).upper()
        
        strength_match = re.search(r'核心优势[\s：:]*([\s\S]*?)(?=\n\n|\n主要风险|\Z)', cleaned_text)
        if strength_match:
            result['core_strengths'] = strength_match.group(1).strip()
        
        risk_match = re.search(r'主要风险[\s：:]*([\s\S]*?)(?=\n\n|\n建议动作|\Z)', cleaned_text)
        if risk_match:
            result['main_risks'] = risk_match.group(1).strip()
        
        action_match = re.search(r'建议动作[\s：:]*([\s\S]*?)(?=\n\n|\Z)', cleaned_text)
        if action_match:
            result['suggested_action'] = action_match.group(1).strip()
        
        reason_match = re.search(r'定级理由[\s：:]*([\s\S]*?)(?=\n\n|\Z)', cleaned_text)
        if reason_match:
            result['rating_reason'] = reason_match.group(1).strip()
        
        module_match = re.search(r'意向[\s：:]*([\s\S]*?)(?=\n\n|\Z)', cleaned_text)
        if module_match:
            result['intention_modules'] = module_match.group(1).strip()
        
        if result['match_score'] > 0:
            return result
        
        logger.warning(f"正则解析也未提取到有效分数，响应前300字: {cleaned_text[:300]}")
        return None
    
    except Exception as e:
        logger.error(f"解析大模型响应失败: {str(e)}")
        return None