"""
简历智能评估系统 - 公共工具模块

该模块提供系统的公共工具功能，包括简历读取、评估标准解析、数据处理和Excel输出。

核心功能：
1. 简历读取：从PDF文件中提取简历内容
2. 评估标准解析：解析评估标准Excel文件
3. 数据处理：处理评估结果（排序、分组、统计）
4. Excel输出：生成格式化的评估结果Excel文件
"""

from .resume_reader import get_all_resumes, read_resumes_for_position, extract_text_from_pdf
from .evaluation_parser import get_all_evaluation_criteria, get_evaluation_criteria, format_evaluation_criteria
from .data_processor import process_evaluation_results, generate_summary_report, sort_candidates_by_priority
from .excel_writer import write_all_positions_excel, write_summary_excel, write_position_excel
