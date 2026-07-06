import logging
import json
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

DEGREE_ORDER = ['博士', '硕士', '本科', '大专', '专科', '高中', '中专']
PRIORITY_RANGES = {
    'P0': (85, 100),
    'P1': (70, 84),
    'P2': (50, 69),
    'P3': (0, 49)
}


def validate_evaluation_result(
    result: Dict[str, Any],
    criteria: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    验证大模型评估结果的正确性
    
    Args:
        result: 评估结果字典
        criteria: 评估标准（包含维度权重信息）
        
    Returns:
        dict: 验证结果，包含：
            - is_valid: 是否通过验证
            - errors: 错误列表
            - warnings: 警告列表
            - details: 详细验证信息
    """
    errors = []
    warnings = []
    details = {}
    
    details['match_score_validation'] = _validate_match_score(result, criteria)
    if details['match_score_validation']['error']:
        errors.append(details['match_score_validation']['error'])
    
    details['priority_validation'] = _validate_priority(result)
    if details['priority_validation']['error']:
        errors.append(details['priority_validation']['error'])
    
    details['dimension_scores_validation'] = _validate_dimension_scores(result, criteria)
    if details['dimension_scores_validation']['error']:
        errors.append(details['dimension_scores_validation']['error'])
    
    details['data_consistency_validation'] = _validate_data_consistency(result)
    if details['data_consistency_validation']['errors']:
        errors.extend(details['data_consistency_validation']['errors'])
    if details['data_consistency_validation']['warnings']:
        warnings.extend(details['data_consistency_validation']['warnings'])
    
    details['action_validation'] = _validate_suggested_action(result)
    if details['action_validation']['warning']:
        warnings.append(details['action_validation']['warning'])
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'details': details
    }


def _validate_match_score(result: Dict[str, Any], criteria: Dict[str, Any] = None) -> Dict[str, Any]:
    """验证匹配度分数"""
    match_score = result.get('match_score', 0)
    
    if not isinstance(match_score, int):
        try:
            match_score = int(float(match_score))
        except (ValueError, TypeError):
            return {
                'error': f"匹配度分数格式错误: {match_score}",
                'expected_range': '0-100',
                'actual_value': match_score,
                'calculated_score': None
            }
    
    if match_score < 0 or match_score > 100:
        return {
            'error': f"匹配度分数超出范围: {match_score}",
            'expected_range': '0-100',
            'actual_value': match_score,
            'calculated_score': None
        }
    
    calculated_score = None
    if criteria and result.get('dimension_scores'):
        dimensions = criteria.get('dimensions', [])
        calculated_score = 0
        for dim in dimensions:
            dim_id = dim.get('id', '')
            weight = dim.get('weight', 0)
            rating = result['dimension_scores'].get(dim_id, 0)
            if isinstance(rating, int) and 0 <= rating <= 5:
                calculated_score += (rating / 5) * weight
        calculated_score = round(calculated_score)
        
        if abs(calculated_score - match_score) > 5:
            return {
                'error': f"匹配度分数与维度计算不一致: 大模型返回{match_score}, 按维度计算应为{calculated_score}",
                'expected_range': '0-100',
                'actual_value': match_score,
                'calculated_score': calculated_score
            }
    
    return {
        'error': None,
        'expected_range': '0-100',
        'actual_value': match_score,
        'calculated_score': calculated_score
    }


def _validate_priority(result: Dict[str, Any]) -> Dict[str, Any]:
    """验证优先级是否与匹配度对应"""
    priority = result.get('priority', '')
    match_score = result.get('match_score', 0)
    
    if priority not in PRIORITY_RANGES:
        return {
            'error': f"优先级值无效: {priority}",
            'expected_values': list(PRIORITY_RANGES.keys()),
            'actual_value': priority,
            'expected_priority': None
        }
    
    if isinstance(match_score, int):
        min_score, max_score = PRIORITY_RANGES[priority]
        if match_score < min_score or match_score > max_score:
            expected_priority = None
            for p, (p_min, p_max) in PRIORITY_RANGES.items():
                if p_min <= match_score <= p_max:
                    expected_priority = p
                    break
            
            return {
                'error': f"优先级与匹配度不匹配: 匹配度{match_score}应属于{expected_priority}，但返回{priority}",
                'expected_values': list(PRIORITY_RANGES.keys()),
                'actual_value': priority,
                'expected_priority': expected_priority
            }
    
    return {
        'error': None,
        'expected_values': list(PRIORITY_RANGES.keys()),
        'actual_value': priority,
        'expected_priority': None
    }


def _validate_dimension_scores(result: Dict[str, Any], criteria: Dict[str, Any] = None) -> Dict[str, Any]:
    """验证维度评分"""
    dimension_scores = result.get('dimension_scores', {})
    
    if not isinstance(dimension_scores, dict):
        return {
            'error': f"dimension_scores格式错误: {type(dimension_scores)}",
            'dimensions': [],
            'invalid_scores': [],
            'missing_dimensions': []
        }
    
    invalid_scores = []
    missing_dimensions = []
    
    if criteria:
        expected_dimensions = criteria.get('dimensions', [])
        expected_ids = [dim.get('id', '') for dim in expected_dimensions if dim.get('id')]
        
        for dim_id in expected_ids:
            if dim_id not in dimension_scores:
                missing_dimensions.append(dim_id)
        
        for dim_id, score in dimension_scores.items():
            if not isinstance(score, int) or score < 0 or score > 5:
                invalid_scores.append({
                    'dimension': dim_id,
                    'score': score,
                    'expected_range': '0-5'
                })
    else:
        for dim_id, score in dimension_scores.items():
            if not isinstance(score, int) or score < 0 or score > 5:
                invalid_scores.append({
                    'dimension': dim_id,
                    'score': score,
                    'expected_range': '0-5'
                })
    
    error_msg = None
    if invalid_scores:
        score_strings = []
        for d in invalid_scores:
            score_strings.append(f"{d['dimension']}={d['score']}")
        error_msg = f"维度评分超出范围(0-5): {', '.join(score_strings)}"
    elif missing_dimensions:
        error_msg = f"缺少维度评分: {', '.join(missing_dimensions)}"
    
    return {
        'error': error_msg,
        'dimensions': list(dimension_scores.keys()),
        'invalid_scores': invalid_scores,
        'missing_dimensions': missing_dimensions
    }


def _validate_data_consistency(result: Dict[str, Any]) -> Dict[str, Any]:
    """验证数据一致性"""
    errors = []
    warnings = []
    
    phone = result.get('phone', '')
    if phone and not phone.isdigit():
        warnings.append(f"手机号格式可能不正确: {phone}")
    
    age = result.get('age', '')
    if age:
        try:
            age_int = int(age)
            if age_int < 18 or age_int > 70:
                warnings.append(f"年龄值异常: {age}")
        except (ValueError, TypeError):
            warnings.append(f"年龄格式不正确: {age}")
    
    education = result.get('education', '')
    if education and education not in DEGREE_ORDER:
        warnings.append(f"学历值不标准: {education}")
    
    match_score = result.get('match_score', 0)
    if isinstance(match_score, int):
        if match_score >= 85 and not result.get('core_strengths'):
            warnings.append("高匹配度(>=85)但缺少核心亮点描述")
        if match_score < 50 and not result.get('main_risks'):
            warnings.append("低匹配度(<50)但缺少主要差距描述")
    
    return {
        'errors': errors,
        'warnings': warnings
    }


def _validate_suggested_action(result: Dict[str, Any]) -> Dict[str, Any]:
    """验证处理动作"""
    action = result.get('suggested_action', '')
    priority = result.get('priority', '')
    
    if not action:
        return {
            'warning': f"缺少处理动作，优先级: {priority}",
            'action': action,
            'priority': priority
        }
    
    expected_actions = {
        'P0': ['直接安排面试', '重点跟进', '优先推荐'],
        'P1': ['安排面试', '验证短板', '推荐'],
        'P2': ['备选', '储备', '视进度'],
        'P3': ['婉拒', '转推荐', '暂不推荐']
    }
    
    if priority in expected_actions:
        expected_keywords = expected_actions[priority]
        if not any(keyword in action for keyword in expected_keywords):
            return {
                'warning': f"处理动作与优先级不匹配: 优先级{priority}期望包含'{expected_keywords}'，实际为'{action}'",
                'action': action,
                'priority': priority,
                'expected_keywords': expected_keywords
            }
    
    return {
        'warning': None,
        'action': action,
        'priority': priority
    }


def generate_validation_report(
    candidate_name: str,
    position: str,
    result: Dict[str, Any],
    criteria: Dict[str, Any] = None
) -> str:
    """
    生成验证报告文本
    
    Args:
        candidate_name: 候选人姓名
        position: 岗位名称
        result: 评估结果
        criteria: 评估标准
        
    Returns:
        str: 格式化的验证报告
    """
    validation = validate_evaluation_result(result, criteria)
    
    report = []
    report.append(f"========== 评估验证报告 ==========")
    report.append(f"候选人: {candidate_name}")
    report.append(f"岗位: {position}")
    report.append(f"验证结果: {'✅ 通过' if validation['is_valid'] else '❌ 不通过'}")
    report.append("")
    
    if validation['errors']:
        report.append("❌ 错误:")
        for error in validation['errors']:
            report.append(f"  - {error}")
        report.append("")
    
    if validation['warnings']:
        report.append("⚠️ 警告:")
        for warning in validation['warnings']:
            report.append(f"  - {warning}")
        report.append("")
    
    report.append("📊 详细验证信息:")
    
    score_val = validation['details']['match_score_validation']
    report.append(f"  匹配度: {score_val['actual_value']}")
    if score_val['calculated_score'] is not None:
        report.append(f"  维度计算: {score_val['calculated_score']}")
        diff = abs(score_val['actual_value'] - score_val['calculated_score'])
        report.append(f"  差异: {diff}分 {'(正常)' if diff <= 5 else '(异常)'}")
    
    priority_val = validation['details']['priority_validation']
    report.append(f"  优先级: {priority_val['actual_value']}")
    
    dim_val = validation['details']['dimension_scores_validation']
    if dim_val['dimensions']:
        report.append(f"  维度评分: {dim_val['dimensions']}")
    
    action_val = validation['details']['action_validation']
    report.append(f"  处理动作: {action_val['action']}")
    
    report.append("")
    report.append("==================================")
    
    return '\n'.join(report)
