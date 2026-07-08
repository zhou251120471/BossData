"""
简历智能评估系统 - 大模型评估标准提取模块

该模块负责使用大模型从评估标准文档（Excel/Word文本）中提取结构化信息，包括：
1. 评估维度：维度ID、维度名称、权重、达标标准、达标标准子项
2. 优先级等级：等级、含义、最低分数、最高分数、处理动作

核心特点：
- 使用大模型理解表格结构和文本内容，提取准确率远高于传统解析方法
- 支持JSON格式输出，便于后续处理
- 提供回退机制，当大模型调用失败时使用传统方法

使用依赖：
- llm.remote_llm.call_llm_api：调用远程大模型API
- config.LLM_CONFIG：大模型配置
- logging：日志记录
- json：JSON数据处理
- re：正则表达式匹配
"""

import re
import json
import logging
from llm.remote_llm import call_llm_api
from config import LLM_CONFIG

logger = logging.getLogger(__name__)

CRITERIA_EXTRACTION_SYSTEM_PROMPT = """你是一个专业的评估标准提取专家，擅长从招聘评估文档中提取评估维度和优先级等级信息。请仔细阅读文档内容，准确提取所有关键信息。"""


def build_criteria_extraction_prompt(doc_text, position_key):
    """
    构建评估标准提取Prompt
    
    将评估标准文档文本和提取要求组合成大模型可理解的Prompt，要求大模型输出JSON格式的结构化信息。
    
    Args:
        doc_text: 评估标准文档文本内容
        position_key: 岗位关键字
        
    Returns:
        str: 构建好的Prompt文本
    """
    prompt = f"""请仔细阅读以下评估标准文档，提取所有评估维度和优先级等级信息，并按照指定的JSON格式输出。

【岗位名称】
{position_key}

【评估标准文档】
{doc_text}

【提取要求】
请从上述文档中提取以下信息：

1. 评估维度（dimensions）：
   每个维度包含：
   - id: 维度标识（如D1、D2、D3、D4）
   - name: 维度名称（如"核心技术栈匹配度"）
   - weight: 权重百分比（整数，如30表示30%）
   - standard: 达标标准（完整的标准描述文本）
   - standard_items: 达标标准子项数组（将标准拆分为具体的子项，每个子项不超过20字）
   - item_count: 达标标准子项数量

2. 优先级等级（priority_levels）：
   每个等级包含：
   - level: 等级标识（P0、P1、P2、P3）
   - meaning: 等级含义（如"优先推荐"、"进入备选池"）
   - min_score: 最低分数（整数，如85表示85%）
   - max_score: 最高分数（整数，如100表示100%）
   - action: 处理动作（如"安排面试"、"进入备选池"）

【输出格式要求】
请严格按照以下JSON格式输出，不要输出其他任何内容：
{{
    "dimensions": [
        {{
            "id": "D1",
            "name": "核心技术栈匹配度",
            "weight": 30,
            "standard": "精通Vue3、TypeScript、Webpack等前端核心技术栈，有组件库开发经验",
            "standard_items": ["精通Vue3", "精通TypeScript", "熟悉Webpack", "有组件库开发经验"],
            "item_count": 4
        }},
        {{
            "id": "D2",
            "name": "经验年限与学历",
            "weight": 20,
            "standard": "本科及以上学历，5年以上前端开发经验",
            "standard_items": ["本科及以上学历", "5年以上前端开发经验"],
            "item_count": 2
        }}
    ],
    "priority_levels": [
        {{
            "level": "P0",
            "meaning": "优先推荐",
            "min_score": 85,
            "max_score": 100,
            "action": "安排面试，重点验证技术深度"
        }},
        {{
            "level": "P1",
            "meaning": "重点考虑",
            "min_score": 70,
            "max_score": 84,
            "action": "安排面试"
        }},
        {{
            "level": "P2",
            "meaning": "进入备选池",
            "min_score": 50,
            "max_score": 69,
            "action": "进入备选池，视进度再议"
        }},
        {{
            "level": "P3",
            "meaning": "婉拒或转推荐",
            "min_score": 0,
            "max_score": 49,
            "action": "婉拒或转推荐至其他岗位"
        }}
    ]
}}

【重要注意事项】
- 如果某个字段在文档中未找到，请填默认值（维度weight默认0，等级分数默认0-100）
- dimensions数组中的维度权重总和应尽量接近100%
- standard_items数组要准确反映达标标准的各个子项
- item_count必须等于standard_items数组的长度
- priority_levels必须包含P0、P1、P2、P3四个等级
- action字段要准确提取文档中的处理动作描述
- 只输出JSON，不要输出其他任何解释或说明文字
"""

    return prompt


def parse_criteria_extraction_response(response_text):
    """
    解析大模型返回的评估标准提取结果
    
    从大模型响应中提取JSON格式的评估标准信息，进行必要的数据清洗和校验。
    
    Args:
        response_text: 大模型返回的文本
        
    Returns:
        dict: 包含提取结果的字典，若解析失败返回None
    """
    if not response_text:
        return None
    
    cleaned_text = response_text.strip()
    
    cleaned_text = re.sub(r'<think>[\s\S]*?</think>', '', cleaned_text)
    
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned_text)
    if code_block_match:
        cleaned_text = code_block_match.group(1).strip()
    
    try:
        json_match = re.search(r'\{[\s\S]*\}', cleaned_text)
        if json_match:
            json_str = json_match.group(0)
            data = json.loads(json_str)
            
            result = {
                'dimensions': [],
                'priority_levels': []
            }
            
            if 'dimensions' in data and isinstance(data['dimensions'], list):
                for dim in data['dimensions']:
                    if isinstance(dim, dict):
                        dim_id = dim.get('id', '').strip()
                        dim_name = dim.get('name', '').strip()
                        
                        weight = 0
                        try:
                            weight = int(dim.get('weight', 0))
                        except:
                            weight_match = re.search(r'(\d+)%', dim.get('standard', ''))
                            if weight_match:
                                weight = int(weight_match.group(1))
                        
                        standard = dim.get('standard', '').strip()
                        standard_items = dim.get('standard_items', [])
                        if isinstance(standard_items, str):
                            standard_items = [item.strip() for item in standard_items.split(';') if item.strip()]
                        elif not isinstance(standard_items, list):
                            standard_items = []
                        
                        item_count = len(standard_items)
                        
                        result['dimensions'].append({
                            'id': dim_id,
                            'name': dim_name,
                            'weight': weight,
                            'standard': standard,
                            'standard_items': standard_items,
                            'item_count': item_count
                        })
            
            if 'priority_levels' in data and isinstance(data['priority_levels'], list):
                for level in data['priority_levels']:
                    if isinstance(level, dict):
                        level_id = level.get('level', '').strip()
                        if level_id not in ['P0', 'P1', 'P2', 'P3']:
                            continue
                        
                        meaning = level.get('meaning', '').strip()
                        
                        min_score = 0
                        try:
                            min_score = int(level.get('min_score', 0))
                        except:
                            pass
                        
                        max_score = 100
                        try:
                            max_score = int(level.get('max_score', 100))
                        except:
                            pass
                        
                        action = level.get('action', '').strip()
                        
                        result['priority_levels'].append({
                            'level': level_id,
                            'meaning': meaning,
                            'min_score': min_score,
                            'max_score': max_score,
                            'action': action
                        })
            
            if result['dimensions']:
                total_weight = sum(dim.get('weight', 0) for dim in result['dimensions'])
                if total_weight != 100:
                    logger.warning(f"评估维度权重总和不是100%: {total_weight}%")
                return result
            
            logger.warning(f"JSON解析成功但dimensions为空，响应前200字: {cleaned_text[:200]}")
            return None
        
        logger.warning(f"未找到JSON格式数据，响应前300字: {cleaned_text[:300]}")
        return None
        
    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失败: {e}")
        return None
    except Exception as e:
        logger.error(f"解析评估标准提取响应失败: {str(e)}")
        return None


def extract_criteria_with_llm(doc_text, position_key, config=None):
    """
    使用大模型提取评估标准
    
    调用大模型API，从评估标准文档文本中提取结构化信息。
    如果大模型调用失败，返回None（由调用方决定是否使用回退方法）。
    
    Args:
        doc_text: 评估标准文档文本内容
        position_key: 岗位关键字
        config: API配置（可选，默认使用LLM_CONFIG）
        
    Returns:
        dict: 包含提取结果的字典，若调用失败返回None
    """
    if not doc_text or len(doc_text.strip()) < 10:
        logger.warning("评估标准文档文本为空或过短，无法提取信息")
        return None
    
    if config is None:
        config = LLM_CONFIG
    
    api_base = config.get('api_base', '')
    api_key = config.get('api_key', '')
    
    if not api_base or not api_key:
        logger.warning("大模型API配置不完整，跳过LLM提取")
        return None
    
    try:
        prompt = build_criteria_extraction_prompt(doc_text, position_key)
        
        extraction_config = config.copy()
        extraction_config['system_prompt'] = CRITERIA_EXTRACTION_SYSTEM_PROMPT
        extraction_config['max_tokens'] = 3000
        
        response = call_llm_api(prompt, config=extraction_config)
        
        if response:
            result = parse_criteria_extraction_response(response)
            if result:
                logger.info(f"LLM评估标准提取成功，岗位: {position_key}，维度数: {len(result.get('dimensions', []))}")
                return result
            logger.warning("LLM评估标准提取响应解析失败")
        
        return None
        
    except Exception as e:
        logger.error(f"使用大模型提取评估标准失败: {str(e)}")
        return None