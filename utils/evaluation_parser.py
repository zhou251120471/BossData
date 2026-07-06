"""
简历智能评估系统 - 评估标准解析模块

该模块负责解析.xlsx格式的评估标准Excel文件，提取评估维度和优先级等级标准。

核心功能：
1. Excel文件解析：使用openpyxl库读取Excel文件中的工作表数据
2. 评估维度提取：从工作表中识别并提取各评估维度的名称、权重和标准
3. 优先级等级提取：从工作表中识别并提取各优先级等级的定义和分数范围
4. 标准格式化：将提取的评估标准格式化为便于大模型理解的文本格式
5. 自动发现：支持自动扫描评估标准目录，发现新的岗位评估标准

使用依赖：
- openpyxl：Excel文件解析
- os：文件系统操作
- logging：日志记录
"""

import os
import re
import logging
from openpyxl import load_workbook
from config import ASSESSMENT_CRITERIA_PATH

logger = logging.getLogger(__name__)

_criteria_cache = {}


def parse_evaluation_excel(excel_path):
    """
    解析评估标准Excel文件，提取评估维度和优先级等级标准
    
    遍历Excel文件中的所有工作表，根据表头内容判断表格类型：
    1. 评估维度表格：表头包含"评估维度"关键字
    2. 优先级等级表格：表头包含"等级"或"优先级"关键字
    
    注意事项：
    - 优先级等级表格需满足行数<=6且尚未提取过优先级等级的条件
    - 优先级等级必须为P0/P1/P2/P3之一才会被提取
    
    Args:
        excel_path: 评估标准Excel文件的路径
        
    Returns:
        dict: 包含dimensions(评估维度)和priority_levels(优先级等级)的字典
    """
    result = {
        'dimensions': [],
        'priority_levels': []
    }
    
    if not os.path.exists(excel_path):
        logger.error(f"评估标准Excel文件不存在: {excel_path}")
        return result
    
    try:
        wb = load_workbook(excel_path, data_only=True)
        
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            
            rows = []
            for row in sheet.iter_rows(values_only=True):
                cells = [str(cell).strip() if cell is not None else '' for cell in row]
                if any(cells):
                    rows.append(cells)
            
            if len(rows) < 2:
                continue
            
            header = rows[0]
            header_str = ' '.join(header)
            
            if '评估维度' in header_str:
                for row in rows[1:]:
                    if len(row) >= 4:
                        dim_id = row[0].strip() if row[0] else ''
                        dim_name = row[1].strip() if row[1] else ''
                        weight = row[2].strip() if row[2] else ''
                        standard = row[3].strip() if row[3] else ''
                        
                        weight_value = 0
                        try:
                            weight_match = re.search(r'(\d+)%', weight)
                            if weight_match:
                                weight_value = int(weight_match.group(1))
                        except:
                            pass
                        
                        standard_items = []
                        if standard:
                            items = re.split(r'[,，;；、。\n]+', standard)
                            for item in items:
                                item = item.strip()
                                if item and len(item) > 2:
                                    standard_items.append(item)
                        
                        result['dimensions'].append({
                            'id': dim_id,
                            'name': dim_name,
                            'weight': weight_value,
                            'standard': standard,
                            'standard_items': standard_items,
                            'item_count': len(standard_items)
                        })
            
            elif '等级' in header_str or '优先级' in header_str:
                if len(rows) <= 6 and len(result['priority_levels']) == 0:
                    for row in rows[1:]:
                        if len(row) >= 4:
                            level = row[0].strip() if row[0] else ''
                            meaning = row[1].strip() if row[1] else ''
                            score_range = row[2].strip() if row[2] else ''
                            action = row[3].strip() if row[3] else ''
                            
                            if level in ['P0', 'P1', 'P2', 'P3']:
                                min_score, max_score = 0, 100
                                try:
                                    score_match = re.search(r'(\d+)%.*?(\d+)%', score_range)
                                    if score_match:
                                        min_score = int(score_match.group(1))
                                        max_score = int(score_match.group(2))
                                    else:
                                        gte_match = re.search(r'≥(\d+)%', score_range)
                                        if gte_match:
                                            min_score = int(gte_match.group(1))
                                            max_score = 100
                                        lt_match = re.search(r'<(\d+)%', score_range)
                                        if lt_match:
                                            max_score = int(lt_match.group(1)) - 1
                                except:
                                    pass
                                
                                result['priority_levels'].append({
                                    'level': level,
                                    'meaning': meaning,
                                    'min_score': min_score,
                                    'max_score': max_score,
                                    'action': action
                                })
        
        total_weight = sum(dim.get('weight', 0) for dim in result['dimensions'])
        if result['dimensions'] and total_weight != 100:
            logger.warning(f"评估维度权重总和不是100%: {total_weight}%, 文件: {excel_path}")
        
        logger.info(f"成功解析评估标准Excel文件: {excel_path}")
        logger.info(f"  - 评估维度: {len(result['dimensions'])}个, 权重总和: {total_weight}%")
        logger.info(f"  - 优先级等级: {len(result['priority_levels'])}个")
        
    except Exception as e:
        logger.error(f"解析评估标准Excel文件失败: {excel_path}, 错误: {str(e)}")
    
    return result


def discover_evaluation_docs():
    """
    自动发现所有评估标准文件
    
    扫描ASSESSMENT_CRITERIA_PATH目录下的所有Excel文件。
    返回文件名到文件路径的映射。
    
    Returns:
        dict: 以Excel文件名为键，文件路径为值的字典
    """
    evaluation_docs = {}
    
    if not os.path.exists(ASSESSMENT_CRITERIA_PATH):
        logger.error(f"评估标准目录不存在: {ASSESSMENT_CRITERIA_PATH}")
        return evaluation_docs
    
    try:
        for filename in os.listdir(ASSESSMENT_CRITERIA_PATH):
            if filename.lower().endswith('.xlsx'):
                evaluation_docs[filename] = os.path.join(ASSESSMENT_CRITERIA_PATH, filename)
                logger.info(f"发现评估标准文件: {filename}")
        
        logger.info(f"共发现 {len(evaluation_docs)} 个评估标准文件")
    except Exception as e:
        logger.error(f"扫描评估标准目录失败: {str(e)}")
    
    return evaluation_docs


def extract_position_from_filename(filename):
    """
    从文件名提取岗位标识
    
    通过匹配模式（如"组·"、"岗位"等）提取岗位关键词。
    
    Args:
        filename: Excel文件名
        
    Returns:
        str: 岗位标识，提取失败返回None
    """
    patterns = [
        r'(.+?)组·',
        r'(.+?)岗位',
        r'(.+?)评估'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, filename)
        if match:
            return match.group(1).strip()
    
    return None


def get_evaluation_criteria(position_key):
    """
    获取指定岗位的评估标准
    
    使用LLM智能匹配找到对应的评估标准文件，然后解析评估标准。
    若匹配失败或文件不存在，返回空的评估标准。
    
    为避免重复读取，使用缓存机制存储已解析的评估标准。
    
    Args:
        position_key: 用户输入的岗位名称
        
    Returns:
        dict: 包含dimensions(评估维度)和priority_levels(优先级等级)的字典
    """
    if position_key in _criteria_cache:
        return _criteria_cache[position_key]
    
    from utils.resource_manager import match_eval_doc
    
    excel_path = match_eval_doc(position_key)
    
    if excel_path and os.path.exists(excel_path):
        # logger.info(f"通过LLM匹配到评估标准文件: {position_key} -> {excel_path}")
        criteria = parse_evaluation_excel(excel_path)
        _criteria_cache[position_key] = criteria
        return criteria
    
    logger.warning(f"未找到匹配的评估标准文件: {position_key}")
    criteria = {
        'dimensions': [],
        'priority_levels': []
    }
    _criteria_cache[position_key] = criteria
    return criteria


def get_all_evaluation_criteria():
    """
    获取所有岗位的评估标准
    
    自动扫描评估标准目录发现所有岗位，逐个调用get_evaluation_criteria函数，
    将结果汇总到字典中返回。支持任意数量的岗位类型。
    
    Returns:
        dict: 以岗位类型为键，评估标准为值的字典
    """
    all_criteria = {}
    evaluation_docs = discover_evaluation_docs()
    
    for position_key in evaluation_docs.keys():
        all_criteria[position_key] = get_evaluation_criteria(position_key)
    
    return all_criteria


def format_evaluation_criteria(position_key):
    """
    格式化评估标准，用于构建Prompt
    
    将评估维度和优先级等级格式化为结构化的文本，便于大模型理解和使用。
    格式示例：
    【前端岗位评估标准】

    一、评估维度及权重：
      D1. 核心技术栈匹配度（权重30%）：精通Vue3...
      D2. 经验年限与学历（权重20%）：本科及以上...

    二、优先级等级标准：
      P0: 优先推荐（匹配度85%-100%），直接安排面试...
    
    Args:
        position_key: 岗位类型关键字
        
    Returns:
        str: 格式化后的评估标准文本
    """
    criteria = get_evaluation_criteria(position_key)
    
    result = f"【{position_key}岗位评估标准】\n\n"
    
    result += "一、评估维度及权重：\n"
    for dim in criteria['dimensions']:
        result += f"  {dim['id']}. {dim['name']}（权重{dim['weight']}%）：{dim['standard']}\n"
    
    result += "\n二、优先级等级标准：\n"
    for level in criteria['priority_levels']:
        result += f"  {level['level']}: {level['meaning']}（匹配度{level['min_score']}%-{level['max_score']}%），{level['action']}\n"
    
    return result