"""
简历智能评估系统 - 资源管理器模块

该模块负责管理和匹配系统中各类资源的路径，包括：
1. 简历目录匹配：根据岗位名查找对应的简历目录
2. 评估标准匹配：根据岗位名查找对应的评估标准Excel文件
3. 规则文件匹配：根据岗位名查找对应的评估规则JSON文件

核心功能：
1. LLM智能匹配：使用大模型判断用户输入与哪个资源最匹配
2. 缓存机制：避免重复扫描目录和调用LLM
3. 统一接口：提供简洁的资源获取接口

使用依赖：
- os：文件系统操作
- logging：日志记录
"""

import os
import logging
from config import BASE_DATA_PATH, RESUMES_PATH, ASSESSMENT_CRITERIA_PATH
from utils.prompt_templates import build_resource_match_prompt, RESOURCE_MATCH_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

POSITION_RULES_DIR = os.path.join(BASE_DATA_PATH, 'data', 'PositionRules')

_use_local_llm = False

_discovered_resources_cache = None
_llm_match_cache = {}


def set_llm_mode(use_local=False):
    """
    设置LLM匹配模式
    
    根据用户选择的评估模式，决定资源匹配时使用远程LLM还是本地LLM。
    必须在任何资源匹配操作之前调用。
    
    Args:
        use_local: 是否使用本地LLM进行资源匹配（默认False，使用远程LLM）
    """
    global _use_local_llm
    _use_local_llm = use_local
    if use_local:
        logger.info("资源匹配模式: 本地大模型")
    else:
        logger.info("资源匹配模式: 远程大模型")


def _discover_all_resources():
    """
    扫描并发现所有可用资源
    
    一次性扫描所有资源目录，构建完整的资源映射表。
    使用缓存机制避免重复扫描。
    
    Returns:
        dict: 包含所有资源的字典
    """
    global _discovered_resources_cache
    
    if _discovered_resources_cache is not None:
        return _discovered_resources_cache
    
    resources = {
        'positions': {},      # 岗位名 -> 详细信息
        'resume_dirs': {},    # 简历目录（原始目录名）
        'eval_docs': {},      # 评估标准文件
        'rule_files': {}      # 规则文件
    }
    
    # 扫描简历目录
    if os.path.exists(RESUMES_PATH):
        for item in os.listdir(RESUMES_PATH):
            item_path = os.path.join(RESUMES_PATH, item)
            if os.path.isdir(item_path):
                resources['resume_dirs'][item] = {
                    'path': item_path,
                    'dir_name': item
                }
    
    # 扫描评估标准目录
    if os.path.exists(ASSESSMENT_CRITERIA_PATH):
        for filename in os.listdir(ASSESSMENT_CRITERIA_PATH):
            if filename.endswith('.xlsx'):
                resources['eval_docs'][filename] = {
                    'path': os.path.join(ASSESSMENT_CRITERIA_PATH, filename),
                    'filename': filename
                }
    
    # 扫描规则文件目录
    if os.path.exists(POSITION_RULES_DIR):
        for filename in os.listdir(POSITION_RULES_DIR):
            if filename.endswith('.json'):
                resources['rule_files'][filename] = {
                    'path': os.path.join(POSITION_RULES_DIR, filename),
                    'filename': filename
                }
    
    _discovered_resources_cache = resources
    logger.info(f"资源扫描完成: "
                f"{len(resources['resume_dirs'])}个简历目录, "
                f"{len(resources['eval_docs'])}个评估标准, "
                f"{len(resources['rule_files'])}个规则文件")
    
    return resources


def _extract_position_from_dir(dir_name):
    """
    从目录名提取岗位标识（用于显示）
    
    Args:
        dir_name: 目录名称
        
    Returns:
        str: 目录名称
    """
    return dir_name


def _build_llm_prompt(user_input, resource_type, resources):
    """
    构建LLM匹配提示词
    
    Args:
        user_input: 用户输入的岗位名称
        resource_type: 资源类型（resume_dirs/eval_docs/rule_files）
        resources: 可用资源字典
        
    Returns:
        str: 提示词
    """
    return build_resource_match_prompt(user_input, resource_type, resources)


def _call_llm_match(user_input, resource_type, resources):
    """
    调用LLM进行智能匹配
    
    根据当前LLM模式选择远程大模型或本地大模型进行语义匹配，
    若LLM不可用，则回退到本地模糊匹配算法。
    
    Args:
        user_input: 用户输入的岗位名称
        resource_type: 资源类型
        resources: 可用资源字典
        
    Returns:
        str: 匹配到的资源名称，未匹配返回None
    """
    cache_key = f"{user_input}_{resource_type}"
    if cache_key in _llm_match_cache:
        return _llm_match_cache[cache_key]
    
    prompt = _build_llm_prompt(user_input, resource_type, resources)
    
    if _use_local_llm:
        response = _call_local_llm_for_match(prompt)
    else:
        response = _call_remote_llm_for_match(prompt)
    
    if response:
        matched = response.strip().strip('"\'').strip()
        
        if matched in resources:
            _llm_match_cache[cache_key] = matched
            logger.info(f"LLM匹配成功: {user_input} -> {matched} ({resource_type})")
            return matched
        
        for resource in resources.keys():
            if matched in resource or resource in matched:
                _llm_match_cache[cache_key] = resource
                logger.info(f"LLM模糊匹配成功: {matched} -> {resource} ({resource_type})")
                return resource
    
    logger.warning(f"LLM匹配失败，尝试本地模糊匹配: {user_input}")
    return _local_fuzzy_match(user_input, resources)


def _call_remote_llm_for_match(prompt):
    """
    调用远程大模型进行资源匹配
    
    Args:
        prompt: 匹配提示词
        
    Returns:
        str: 模型响应文本，失败返回None
    """
    try:
        from llm.remote_llm import call_llm_api
        from config import LLM_CONFIG
        
        match_config = LLM_CONFIG.copy()
        match_config['system_prompt'] = RESOURCE_MATCH_SYSTEM_PROMPT
        
        return call_llm_api(prompt, config=match_config)
    except Exception as e:
        logger.warning(f"远程LLM调用异常: {str(e)}")
        return None


def _call_local_llm_for_match(prompt):
    """
    调用本地大模型进行资源匹配
    
    Args:
        prompt: 匹配提示词
        
    Returns:
        str: 模型响应文本，失败返回None
    """
    try:
        from local_llm.local_model import call_local_model
        
        return call_local_model(prompt)
    except Exception as e:
        logger.warning(f"本地LLM调用异常: {str(e)}")
        return None


def _local_fuzzy_match(user_input, resources):
    """
    本地模糊匹配（备用方案）
    
    当LLM不可用时，使用字符串相似度和包含关系进行匹配。
    
    匹配策略：
    1. 精确匹配
    2. 包含匹配（输入在资源名中，或资源名在输入中）
    3. 编辑距离相似度匹配
    
    Args:
        user_input: 用户输入的岗位名称
        resources: 可用资源字典
        
    Returns:
        str: 匹配到的资源名称，未匹配返回None
    """
    input_lower = user_input.lower()
    
    # 1. 精确匹配
    if user_input in resources:
        logger.info(f"精确匹配成功: {user_input}")
        return user_input
    
    # 2. 包含匹配
    for resource in resources.keys():
        resource_lower = resource.lower()
        if input_lower in resource_lower or resource_lower in input_lower:
            logger.info(f"包含匹配成功: {user_input} -> {resource}")
            return resource
    
    # 3. 编辑距离相似度匹配
    from difflib import SequenceMatcher
    
    best_score = 0
    best_match = None
    
    for resource in resources.keys():
        # 使用SequenceMatcher计算相似度
        score = SequenceMatcher(None, user_input, resource).ratio()
        
        # 字符重叠度
        input_chars = set(user_input)
        resource_chars = set(resource)
        char_overlap = len(input_chars & resource_chars) / max(len(input_chars), len(resource_chars))
        
        # 综合得分（编辑距离 + 字符重叠度）
        combined_score = (score + char_overlap) / 2
        
        if combined_score > best_score and combined_score >= 0.5:
            best_score = combined_score
            best_match = resource
    
    if best_match:
        logger.info(f"相似度匹配成功: {user_input} -> {best_match} (相似度: {best_score:.2f})")
        return best_match
    
    logger.warning(f"本地匹配也失败: {user_input}")
    return None


def match_resume_dir(user_input):
    """
    匹配简历目录
    
    使用LLM判断用户输入与哪个简历目录最匹配。
    
    Args:
        user_input: 用户输入的岗位名称
        
    Returns:
        str: 简历目录路径，未匹配返回None
    """
    resources = _discover_all_resources()
    
    if not resources['resume_dirs']:
        return None
    
    # 如果只有一个，直接返回
    if len(resources['resume_dirs']) == 1:
        return list(resources['resume_dirs'].values())[0]['path']
    
    matched_name = _call_llm_match(user_input, '简历目录', resources['resume_dirs'])
    
    if matched_name and matched_name in resources['resume_dirs']:
        return resources['resume_dirs'][matched_name]['path']
    
    return None


def match_eval_doc(user_input):
    """
    匹配评估标准文件
    
    使用LLM判断用户输入与哪个评估标准文件最匹配。
    
    Args:
        user_input: 用户输入的岗位名称
        
    Returns:
        str: 评估标准文件路径，未匹配返回None
    """
    resources = _discover_all_resources()
    
    if not resources['eval_docs']:
        return None
    
    # 如果只有一个，直接返回
    if len(resources['eval_docs']) == 1:
        return list(resources['eval_docs'].values())[0]['path']
    
    matched_name = _call_llm_match(user_input, '评估标准', resources['eval_docs'])
    
    if matched_name and matched_name in resources['eval_docs']:
        return resources['eval_docs'][matched_name]['path']
    
    return None


def match_rule_file(user_input):
    """
    匹配规则文件
    
    使用LLM判断用户输入与哪个规则文件最匹配。
    
    Args:
        user_input: 用户输入的岗位名称
        
    Returns:
        str: 规则文件路径，未匹配返回None
    """
    resources = _discover_all_resources()
    
    if not resources['rule_files']:
        return None
    
    # 如果只有一个，直接返回
    if len(resources['rule_files']) == 1:
        return list(resources['rule_files'].values())[0]['path']
    
    matched_name = _call_llm_match(user_input, '规则文件', resources['rule_files'])
    
    if matched_name and matched_name in resources['rule_files']:
        return resources['rule_files'][matched_name]['path']
    
    return None


def get_all_resume_dirs():
    """
    获取所有简历目录
    
    Returns:
        dict: 简历目录字典 {目录名: 路径}
    """
    resources = _discover_all_resources()
    return {k: v['path'] for k, v in resources['resume_dirs'].items()}


def match_position_name(user_input):
    """
    匹配岗位目录名称
    
    根据用户输入匹配最接近的简历目录名称。
    先尝试LLM智能匹配，失败则回退到本地模糊匹配。
    
    Args:
        user_input: 用户输入的岗位名称（如"前端"）
        
    Returns:
        str: 匹配到的目录名称（如"前端开发人员的简历"），未匹配返回None
    """
    resources = _discover_all_resources()
    
    if not resources['resume_dirs']:
        return None
    
    if len(resources['resume_dirs']) == 1:
        return list(resources['resume_dirs'].keys())[0]
    
    matched_name = _call_llm_match(user_input, '简历目录', resources['resume_dirs'])
    
    if matched_name and matched_name in resources['resume_dirs']:
        return matched_name
    
    return None


def get_all_positions():
    """
    获取所有已发现的岗位列表
    
    Returns:
        list: 岗位名称列表
    """
    resources = _discover_all_resources()
    return list(resources['resume_dirs'].keys())


def clear_cache():
    """
    清除所有缓存
    
    下次访问时会重新扫描目录和调用LLM。
    """
    global _discovered_resources_cache, _llm_match_cache
    _discovered_resources_cache = None
    _llm_match_cache = {}
    logger.info("资源缓存已清除")


def print_all_resources():
    """
    打印所有已发现的资源（用于调试）
    """
    resources = _discover_all_resources()
    
    print("\n=== 已发现的资源 ===\n")
    
    print("简历目录:")
    for name, info in resources['resume_dirs'].items():
        print(f"  - {name}")
    
    print("\n评估标准文件:")
    for name, info in resources['eval_docs'].items():
        print(f"  - {name}")
    
    print("\n规则文件:")
    for name, info in resources['rule_files'].items():
        print(f"  - {name}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    
    # 打印所有资源
    print_all_resources()
    
    # 测试匹配功能
    print("\n=== LLM匹配测试 ===\n")
    test_inputs = ['前端', '美工设计', 'UI', '测试', '前端开发']
    
    for inp in test_inputs:
        resume = match_resume_dir(inp)
        rule = match_rule_file(inp)
        print(f"输入: '{inp}'")
        print(f"  简历目录: {resume}")
        print(f"  规则文件: {rule}")
        print()