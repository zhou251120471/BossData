"""
简历智能评估系统 - 数据处理模块

该模块负责处理评估结果，包括排序、分组、统计和报告生成。

核心功能：
1. 排序：按优先级等级和匹配度对候选人进行排序
2. 分组：按优先级等级对候选人进行分组
3. 排名：为排序后的候选人添加排名
4. 统计：计算各优先级等级的人数分布
5. 格式化：格式化候选人信息用于输出
6. 报告生成：生成评估汇总报告文本

使用依赖：
- logging：日志记录
"""

import logging
from config import PRIORITY_ORDER, PRIORITY_LEVELS

logger = logging.getLogger(__name__)


def sort_candidates_by_priority(candidates):
    """
    按优先级排序候选人
    
    排序规则：
    1. 首先按优先级等级排序（P0 > P1 > P2 > P3）
    2. 同优先级按匹配度降序排列
    
    使用PRIORITY_ORDER定义的优先级顺序，将优先级转换为索引进行排序。
    
    Args:
        candidates: 候选人列表
        
    Returns:
        list: 排序后的候选人列表
    """
    priority_map = {p: i for i, p in enumerate(PRIORITY_ORDER)}
    
    sorted_list = sorted(
        candidates,
        key=lambda c: (
            priority_map.get(c.get('priority', 'P3'), 4),
            -c.get('match_score', 0)
        )
    )
    
    return sorted_list


def group_candidates_by_priority(candidates):
    """
    按优先级分组候选人
    
    将候选人按优先级等级分组，每组内按匹配度降序排列。
    返回的字典包含P0、P1、P2、P3四个键，值为对应优先级的候选人列表。
    
    Args:
        candidates: 候选人列表
        
    Returns:
        dict: 以优先级为键，候选人列表为值的字典
    """
    grouped = {p: [] for p in PRIORITY_ORDER}
    
    for candidate in candidates:
        priority = candidate.get('priority', 'P3')
        if priority in grouped:
            grouped[priority].append(candidate)
        else:
            grouped['P3'].append(candidate)
    
    for priority in grouped:
        grouped[priority] = sorted(
            grouped[priority],
            key=lambda c: -c.get('match_score', 0)
        )
    
    return grouped


def add_rank_to_candidates(candidates):
    """
    为候选人添加排名
    
    遍历排序后的候选人列表，依次添加排名序号（从1开始）。
    排名信息存储在候选人字典的'rank'字段中。
    
    Args:
        candidates: 已排序的候选人列表
        
    Returns:
        list: 添加排名后的候选人列表
    """
    for i, candidate in enumerate(candidates, 1):
        candidate['rank'] = i
    
    return candidates


def calculate_priority_distribution(candidates):
    """
    计算各优先级等级的人数分布
    
    统计每个优先级等级的人数，以及总人数。
    返回的字典包含P0、P1、P2、P3四个优先级的人数，以及'total'键存储总人数。
    
    Args:
        candidates: 候选人列表
        
    Returns:
        dict: 各优先级人数统计
    """
    distribution = {p: 0 for p in PRIORITY_ORDER}
    distribution['total'] = len(candidates)
    
    for candidate in candidates:
        priority = candidate.get('priority', 'P3')
        if priority in distribution:
            distribution[priority] += 1
    
    return distribution


def format_candidate_for_output(candidate):
    """
    格式化候选人信息用于输出
    
    将候选人信息格式化为适合Excel输出的字典，包含以下字段：
    - 排名：候选人排名
    - 姓名：候选人姓名
    - 岗位：应聘岗位
    - 年限：工作年限
    - 学历：学历信息
    - 匹配度：匹配度百分比（如"85%"）
    - 优先级：优先级等级
    - 核心优势：核心优势描述
    - 主要风险：主要风险描述
    - 建议动作：建议动作
    
    Args:
        candidate: 候选人信息字典
        
    Returns:
        dict: 格式化后的候选人信息
    """
    return {
        'rank': candidate.get('rank', ''),
        'name': candidate.get('name', ''),
        'position': candidate.get('position', ''),
        'experience': candidate.get('experience', ''),
        'education': candidate.get('education', ''),
        'match_score': f"{candidate.get('match_score', 0)}%",
        'priority': candidate.get('priority', ''),
        'core_strengths': candidate.get('core_strengths', ''),
        'main_risks': candidate.get('main_risks', ''),
        'suggested_action': candidate.get('suggested_action', '')
    }


def process_evaluation_results(all_evaluated):
    """
    处理所有评估结果，进行排序和分组
    
    对每个岗位的评估结果执行以下操作：
    1. 按优先级排序候选人
    2. 添加排名
    3. 按优先级分组
    4. 计算优先级分布统计
    
    Args:
        all_evaluated: 所有岗位的评估结果字典（岗位类型 -> 候选人列表）
        
    Returns:
        dict: 处理后的结果，包含排序后的列表、分组信息和分布统计
    """
    processed = {}
    
    for position, candidates in all_evaluated.items():
        sorted_candidates = sort_candidates_by_priority(candidates)
        sorted_candidates = add_rank_to_candidates(sorted_candidates)
        
        grouped = group_candidates_by_priority(candidates)
        distribution = calculate_priority_distribution(candidates)
        
        processed[position] = {
            'sorted_list': sorted_candidates,
            'grouped': grouped,
            'distribution': distribution
        }
        
        logger.info(f"{position}岗位评估完成 - 总人数: {distribution['total']}, P0: {distribution['P0']}, P1: {distribution['P1']}, P2: {distribution['P2']}, P3: {distribution['P3']}")
    
    return processed


def generate_summary_report(processed_results):
    """
    生成评估汇总报告
    
    将处理后的评估结果格式化为文本报告，包含：
    1. 每个岗位的评估统计（总人数、各优先级人数）
    2. 所有岗位的汇总统计
    
    Args:
        processed_results: 处理后的评估结果
        
    Returns:
        str: 汇总报告文本
    """
    report = "=" * 60 + "\n"
    report += "          简历智能评估系统 - 评估汇总报告\n"
    report += "=" * 60 + "\n\n"
    
    total_candidates = 0
    total_p0 = 0
    total_p1 = 0
    total_p2 = 0
    total_p3 = 0
    
    for position, data in processed_results.items():
        distribution = data['distribution']
        
        report += f"【{position}岗位】\n"
        report += f"  总人数: {distribution['total']}人\n"
        report += f"  P0(优先推荐): {distribution['P0']}人\n"
        report += f"  P1(推荐): {distribution['P1']}人\n"
        report += f"  P2(备选): {distribution['P2']}人\n"
        report += f"  P3(暂不推荐): {distribution['P3']}人\n"
        report += "\n"
        
        total_candidates += distribution['total']
        total_p0 += distribution['P0']
        total_p1 += distribution['P1']
        total_p2 += distribution['P2']
        total_p3 += distribution['P3']
    
    report += "=" * 60 + "\n"
    report += f"【总计】\n"
    report += f"  总人数: {total_candidates}人\n"
    report += f"  P0(优先推荐): {total_p0}人\n"
    report += f"  P1(推荐): {total_p1}人\n"
    report += f"  P2(备选): {total_p2}人\n"
    report += f"  P3(暂不推荐): {total_p3}人\n"
    report += "=" * 60 + "\n"
    
    return report
