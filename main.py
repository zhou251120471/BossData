"""
简历智能评估系统 - 主程序入口

该模块是系统的主入口，负责整合所有模块并执行完整的评估流程。

评估流程：
1. 读取简历文件：从指定目录读取所有岗位的PDF简历
2. 解析评估标准：从Excel文件中提取评估维度和优先级等级标准
3. 评估候选人：使用远程大模型或本地大模型对候选人进行评估
4. 处理评估结果：排序、分组、统计、生成报告
5. 生成Excel文件：输出各岗位评估结果和汇总报告

使用方法：
    python main.py --llm              # 使用阿里云百炼大模型评估所有岗位
    python main.py --local            # 使用本地模型评估所有岗位（GPU加速）
    python main.py --llm --positions 前端,测试 # 使用阿里云大模型评估指定岗位
    python main.py --local --positions 前端    # 使用本地模型评估指定岗位
"""

import os
import sys
import argparse
import logging
import logging.config
import time

from config import LOGGING_CONFIG, LLM_CONFIG, PRIORITY_LEVELS
from utils.resume_reader import get_all_resumes, get_position_list, read_resumes_for_position_with_llm, read_resumes_for_position
from utils.evaluation_parser import get_evaluation_criteria, get_evaluation_criteria_with_llm, format_evaluation_criteria, get_all_evaluation_criteria
from utils.data_processor import process_evaluation_results, generate_summary_report
from utils.excel_writer import write_all_positions_excel
from utils.resource_manager import set_llm_mode, match_position_name, match_resume_dir, match_eval_doc, get_all_resume_dirs
from local_llm.local_model import detect_gpu, call_local_model
from llm.remote_llm import call_llm_api, parse_llm_response, build_evaluation_prompt

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def print_progress(current, total, task_name):
    """
    鎵撳嵃杩涘害鏉?    
    鍦ㄦ帶鍒跺彴杈撳嚭杩涘害鏉★紝鏄剧ず褰撳墠杩涘害鐧惧垎姣斿拰宸插鐞嗘暟閲?鎬绘暟閲忋€?    
    Args:
        current: 褰撳墠杩涘害锛堝凡澶勭悊鏁伴噺锛?        total: 鎬绘暟閲?        task_name: 浠诲姟鍚嶇О
    """
    progress = (current / total) * 100
    bar_length = 50
    filled_length = int(bar_length * current // total)
    bar = '=' * filled_length + '-' * (bar_length - filled_length)
    print(f"\r{task_name}: [{bar}] {progress:.1f}% ({current}/{total})", end='')


def evaluate_candidate(candidate, position_key, use_llm=False, use_local=False, criteria=None):
    """
    评估单个候选人
    
    根据参数选择评估方式：
    - use_local=True: 使用本地LLM模型评估
    - use_llm=True: 使用远程LLM评估
    - 都为False: 返回默认评估结果
    
    Args:
        candidate: 候选人信息字典
        position_key: 职位关键字
        use_llm: 是否使用远程LLM
        use_local: 是否使用本地LLM
        criteria: 预读取的评估标准（可选），避免重复读取
        
    Returns:
        dict: 评估结果
    """
    try:
        if criteria is None:
            criteria = get_all_evaluation_criteria().get(position_key, {})
        
        if use_local:
            prompt = build_evaluation_prompt(candidate, position_key, use_local=True)
            response = call_local_model(prompt)
            if response:
                logger.info(f"本地模型原始响应(前500字): {response[:500]}")
                result = parse_llm_response(response)
                if result:
                    priority = result.get('priority', 'P3')
                    priority_levels = criteria.get('priority_levels', [])
                    
                    action_from_doc = ''
                    for level in priority_levels:
                        if level.get('level') == priority:
                            action_from_doc = level.get('action', '')
                            break
                    
                    if action_from_doc:
                        result['suggested_action'] = action_from_doc
                    
                    return result
                logger.warning(f"解析本地模型响应失败: {position_key} - {candidate.get('name', 'unknown')}")
                logger.warning(f"本地模型响应内容(前300字): {response[:300]}")
            else:
                logger.warning(f"本地模型返回为空: {position_key} - {candidate.get('name', 'unknown')}")
        
        elif use_llm:
            prompt = build_evaluation_prompt(candidate, position_key, use_local=False)
            response = call_llm_api(prompt)
            if response:
                result = parse_llm_response(response)
                if result:
                    priority = result.get('priority', 'P3')
                    priority_levels = criteria.get('priority_levels', [])
                    
                    action_from_doc = ''
                    for level in priority_levels:
                        if level.get('level') == priority:
                            action_from_doc = level.get('action', '')
                            break
                    
                    if action_from_doc:
                        result['suggested_action'] = action_from_doc
                    
                    return result
                logger.warning(f"解析远程LLM响应失败: {position_key} - {candidate.get('name', 'unknown')}")
        
        # 默认规则评估（按维度计算）
        dimensions = criteria.get('dimensions', [])
        
        match_score = 0
        dimension_scores = {}
        dimension_details = {}
        
        full_text = (candidate.get('full_text', '') + ' ' + 
                     candidate.get('skills', '') + ' ' + 
                     candidate.get('summary', '')).lower()
        
        for dim in dimensions:
            dim_id = dim.get('id', '')
            dim_weight = dim.get('weight', 0)
            items = dim.get('standard_items', [])
            
            keywords = []
            for item in items:
                if item:
                    sub_keywords = re.split(r'[/+、,，;；()（）·\s]+', item)
                    for kw in sub_keywords:
                        kw = kw.strip()
                        if kw and len(kw) >= 2:
                            keywords.append(kw)
            
            matched_keywords = []
            for kw in keywords:
                if kw.lower() in full_text:
                    matched_keywords.append(kw)
            
            total_keywords = len(keywords) if keywords else 1
            match_ratio = len(matched_keywords) / total_keywords if total_keywords > 0 else 0
            
            max_score = 5
            dim_score = int(match_ratio * max_score)
            
            if dim_score > max_score:
                dim_score = max_score
            
            weighted_score = int(match_ratio * dim_weight)
            
            dimension_scores[dim_id] = dim_score
            dimension_details[dim_id] = {
                'matched_items': len(matched_keywords),
                'total_items': total_keywords,
                'weighted_score': str(weighted_score),
                'matched_keywords': matched_keywords[:5]
            }
            
            match_score += weighted_score
        
        match_score = min(match_score, 100)
        
        priority = 'P3'
        if match_score >= 85:
            priority = 'P0'
        elif match_score >= 70:
            priority = 'P1'
        elif match_score >= 50:
            priority = 'P2'
        
        priority_levels = criteria.get('priority_levels', [])
        action = ''
        for level in priority_levels:
            if level.get('level') == priority:
                action = level.get('action', '')
                break
        
        if not action:
            action = PRIORITY_LEVELS.get(priority, {}).get('action', '储备人才')
        
        return {
            'match_score': match_score,
            'priority': priority,
            'core_strengths': f"匹配了 {sum(d.get('matched_items', 0) for d in dimension_details.values())} 个评估项",
            'main_risks': '',
            'suggested_action': action,
            'rating_reason': f"规则匹配得分: {match_score}%",
            'intention_modules': candidate.get('position', ''),
            'preliminary_info': candidate.get('experience', '') + ' ' + candidate.get('education', ''),
            'dimension_scores': dimension_scores,
            'dimension_details': dimension_details
        }
    
    except Exception as e:
        logger.error(f"评估候选人失败: {candidate.get('name', 'unknown')}, 错误: {str(e)}")
        return {
            'match_score': 0,
            'priority': 'P3',
            'core_strengths': '',
            'main_risks': '评估过程出错',
            'suggested_action': '跳过',
            'rating_reason': '评估异常',
            'intention_modules': '',
            'preliminary_info': '',
            'dimension_scores': {},
            'dimension_details': {}
        }


def evaluate_all_candidates(candidates, position_key, use_llm=False, use_local=False, criteria=None):
    """
    评估所有候选人
    
    Args:
        candidates: 候选人列表
        position_key: 职位关键字
        use_llm: 是否使用远程LLM
        use_local: 是否使用本地LLM
        criteria: 预读取的评估标准（可选），避免重复读取
        
    Returns:
        list: 评估结果列表
    """
    evaluated = []
    total = len(candidates)
    
    for idx, candidate in enumerate(candidates, 1):
        result = evaluate_candidate(candidate, position_key, use_llm, use_local, criteria)
        
        evaluated.append({
            **candidate,
            **result
        })
        
        name = candidate.get('name', '未知')
        score = result.get('match_score', 0)
        priority = result.get('priority', 'N/A')
        logger.info(f"  [{idx}/{total}] {name} | 匹配度: {score}% | 优先级: {priority}")
    
    return evaluated


def run_evaluation(use_llm=False, use_local=False, positions=None):
    """
    运行完整的评估流程
    
    执行以下步骤：
    1. 匹配资源：根据岗位关键词匹配简历目录和评估标准文件
    2. 读取简历文件：只读取匹配的简历目录下的PDF简历
    3. 解析评估标准：只读取匹配的评估标准文件
    4. 评估候选人：逐个简历与评估标准一起发送给大模型评估
    5. 处理评估结果：排序、分组、统计、生成报告
    6. 生成Excel文件：输出各岗位评估结果和汇总报告
    
    评估方式选择：
    - use_local=True: 使用本地模型评估（GPU加速）
    - use_llm=True: 使用阿里云百炼大模型评估
    - 都为False: 使用本地规则评估
    
    Args:
        use_llm: 是否使用阿里云大模型评估（默认False）
        use_local: 是否使用本地模型评估（默认False）
        positions: 指定评估的岗位列表（可选），None表示评估所有岗位
        
    Returns:
        dict: 处理后的评估结果
    """
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("          简历智能评估系统 - 开始评估")
    logger.info("=" * 60)
    
    if use_llm and (not LLM_CONFIG.get('api_base') or not LLM_CONFIG.get('api_key')):
        logger.warning("大模型API配置不完整，自动切换到本地规则评估模式")
        use_llm = False
    
    if use_local:
        gpu_info = detect_gpu()
        logger.info(f"评估模式: 本地模型评估")
        if gpu_info['has_gpu']:
            logger.info(f"  设备: {gpu_info['device_type'].upper()} - {gpu_info['gpu_name']} ({gpu_info['gpu_memory']})")
        else:
            logger.info(f"  设备: CPU（未检测到GPU，推理速度较慢）")
    elif use_llm:
        logger.info(f"评估模式: 阿里云百炼大模型评估 ({LLM_CONFIG.get('model', '')})")
    else:
        logger.info("评估模式: 本地规则评估")
    
    if positions:
        logger.info(f"评估岗位: {', '.join(positions)}")
    else:
        logger.info("评估岗位: 全部岗位")
    
    logger.info("")
    
    logger.info("步骤1/4: 匹配资源...")
    
    if positions:
        all_resumes = {}
        all_criteria = {}
        
        for user_input in positions:
            matched_dir_name = match_position_name(user_input)
            resume_dir = match_resume_dir(user_input)
            eval_doc_path = match_eval_doc(user_input)
            
            if not resume_dir:
                logger.warning(f"  未匹配到简历目录: '{user_input}'")
                continue
            
            if not eval_doc_path:
                logger.warning(f"  未匹配到评估标准文件: '{user_input}'")
                continue
            
            logger.info(f"  岗位匹配: '{user_input}'")
            logger.info(f"    简历目录: {resume_dir}")
            logger.info(f"    评估标准: {eval_doc_path}")
            
            if use_llm:
                candidates = read_resumes_for_position_with_llm(matched_dir_name, resume_dir)
                criteria = get_evaluation_criteria_with_llm(user_input)
            else:
                candidates = read_resumes_for_position(matched_dir_name, resume_dir)
                criteria = get_evaluation_criteria(user_input)
            
            all_resumes[matched_dir_name] = candidates
            all_criteria[matched_dir_name] = criteria
            
            logger.info(f"    读取简历: {len(candidates)}份")
            logger.info(f"    评估维度: {len(criteria['dimensions'])}个")
    
    else:
        logger.info("  评估全部岗位，自动扫描资源...")
        
        resume_dirs = get_all_resume_dirs()
        
        all_resumes = {}
        all_criteria = {}
        
        for dir_name, resume_dir in resume_dirs.items():
            logger.info(f"  处理岗位: {dir_name}")
            
            eval_doc_path = match_eval_doc(dir_name)
            if not eval_doc_path:
                logger.warning(f"    未匹配到评估标准文件，跳过")
                continue
            
            logger.info(f"    简历目录: {resume_dir}")
            logger.info(f"    评估标准: {eval_doc_path}")
            
            if use_llm:
                candidates = read_resumes_for_position_with_llm(dir_name, resume_dir)
                criteria = get_evaluation_criteria_with_llm(dir_name)
            else:
                candidates = read_resumes_for_position(dir_name, resume_dir)
                criteria = get_evaluation_criteria(dir_name)
            
            all_resumes[dir_name] = candidates
            all_criteria[dir_name] = criteria
            
            logger.info(f"    读取简历: {len(candidates)}份")
            logger.info(f"    评估维度: {len(criteria['dimensions'])}个")
    
    total_candidates = sum(len(candidates) for candidates in all_resumes.values())
    logger.info(f"\n  共匹配 {len(all_resumes)} 个岗位，读取 {total_candidates} 份简历")
    
    if total_candidates == 0:
        logger.error("未读取到任何简历，请检查数据目录配置")
        return {}
    
    logger.info("")
    
    logger.info("步骤2/4: 评估候选人...")
    
    all_evaluated = {}
    total_processed = 0
    
    for position, candidates in all_resumes.items():
        if not candidates:
            continue
        
        logger.info(f"  正在评估 {position}岗位 ({len(candidates)}人)...")
        
        criteria = all_criteria.get(position, {})
        evaluated = evaluate_all_candidates(candidates, position, use_llm, use_local, criteria)
        all_evaluated[position] = evaluated
        
        total_processed += len(evaluated)
        print_progress(total_processed, total_candidates, "评估进度")
    
    print()
    logger.info(f"  完成评估: {total_processed}人")
    
    logger.info("")
    
    logger.info("步骤3/4: 处理评估结果...")
    processed = process_evaluation_results(all_evaluated)
    
    report = generate_summary_report(processed)
    logger.info("\n" + report)
    
    logger.info("")
    
    logger.info("步骤4/4: 生成Excel文件...")
    
    file_paths = write_all_positions_excel(processed, criteria_dict=all_criteria)
    logger.info("")
    logger.info("生成的文件:")
    for position, path in file_paths.items():
        logger.info(f"  - {position}岗位: {path}")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"          评估完成! 耗时: {elapsed_time:.2f}秒")
    logger.info("=" * 60)
    
    return processed


def main():
    """
    主程序入口
    
    使用argparse解析命令行参数并执行评估流程：
    - --llm：使用阿里云百炼大模型评估
    - --local：使用本地模型评估（GPU加速）
    - --positions 岗位1,岗位2：指定评估的岗位（默认评估所有岗位）
    - --help/-h：显示帮助信息和可用职位列表
    
    使用方法:
        python main.py --llm              # 使用阿里云百炼大模型评估所有岗位
        python main.py --local            # 使用本地模型评估所有岗位（GPU加速）
        python main.py --llm --positions 前端,测试 # 使用阿里云大模型评估前端和测试岗位
        python main.py --local --positions 前端    # 使用本地模型评估前端岗位
    """
    available_positions = get_position_list()
    
    parser = argparse.ArgumentParser(
        description='简历智能评估系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
使用示例:
  python main.py --llm              # 使用阿里云百炼大模型评估所有岗位
  python main.py --local            # 使用本地模型评估所有岗位（GPU加速）
  python main.py --llm --positions 前端,测试 # 使用阿里云大模型评估指定岗位
  python main.py --local --positions 前端    # 使用本地模型评估指定岗位

可用岗位: {', '.join(available_positions) if available_positions else '未发现岗位'}

注意:
  - 使用--llm前请先配置config.py中的LLM_CONFIG
  - 使用--local前请确保模型文件已下载到model目录
  - 本地模型需要GPU支持，否则推理速度较慢
"""
    )
    
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--llm', action='store_true', help='使用阿里云百炼大模型评估')
    mode_group.add_argument('--local', action='store_true', help='使用本地模型评估（GPU加速）')
    
    parser.add_argument('--positions', type=str, default=None,
                       help='指定评估的岗位，多个岗位用逗号分隔，如：前端,测试')
    
    args = parser.parse_args()
    
    use_llm = args.llm
    use_local = args.local
    positions = None
    if args.positions:
        positions = [p.strip() for p in args.positions.split(',')]
    
    set_llm_mode(use_local=use_local)
    
    try:
        run_evaluation(use_llm=use_llm, use_local=use_local, positions=positions)
    except Exception as e:
        logger.error(f"评估过程中发生错误: {str(e)}", exc_info=True)
        print(f"\n评估失败: {str(e)}")


if __name__ == '__main__':
    """
    程序入口
    
    当直接运行该脚本时，调用main函数执行评估流程。
    """
    main()