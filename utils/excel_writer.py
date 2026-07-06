"""
简历智能评估系统 - Excel输出模块

该模块负责生成格式化的Excel评估结果文件。

核心功能：
1. 输出目录管理：创建输出目录（如果不存在）
2. 列宽计算：根据表头和数据内容自动计算列宽
3. 样式应用：应用表头样式、数据行样式和优先级着色
4. 模板加载：加载输出模板文件，保持格式一致性
5. 单岗位输出：为单个岗位生成Excel评估结果文件
6. 多岗位输出：为所有岗位批量生成Excel评估结果文件
7. 汇总报告：生成包含所有岗位评估统计的汇总Excel文件

使用依赖：
- openpyxl：Excel文件操作
- os：文件系统操作
- logging：日志记录
"""

import os
import logging
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from config import OUTPUT_PATH, OUTPUT_COLUMNS, OUTPUT_TEMPLATE_PATH, PRIORITY_ORDER

logger = logging.getLogger(__name__)


def get_timestamp():
    """
    获取当前时间戳字符串
    
    用于文件命名，格式为 YYYYMMDD_HHMMSS
    
    Returns:
        str: 时间戳字符串
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_output_directory():
    """
    创建输出目录
    
    检查OUTPUT_PATH指定的目录是否存在，如果不存在则创建。
    
    Returns:
        str: 输出目录路径
    """
    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH)
        logger.info(f"创建输出目录: {OUTPUT_PATH}")
    
    return OUTPUT_PATH


def get_column_widths(headers, data_rows):
    """
    计算各列的宽度
    
    根据表头和数据行内容的长度计算列宽，确保内容能够完整显示。
    列宽计算规则：
    - 基础宽度：中文长度 * 1.5，英文长度 * 0.9
    - 最小宽度：8（适用于序号等短列）
    - 最大宽度：60（适用于核心亮点等长文本列）
    - 特殊列宽度：
      - 手机号：15
      - 年龄：8
      - 综合匹配度：12
      - 优先级：8
      - 处理动作：18
    
    Args:
        headers: 表头列表
        data_rows: 数据行列表
        
    Returns:
        list: 各列宽度列表
    """
    base_widths = []
    
    for h in headers:
        h_str = str(h)
        chinese_count = sum(1 for c in h_str if '\u4e00' <= c <= '\u9fff')
        english_count = len(h_str) - chinese_count
        base_width = chinese_count * 1.5 + english_count * 0.9
        
        if '手机号' in h_str:
            base_width = max(base_width, 15)
        elif '年龄' in h_str:
            base_width = max(base_width, 8)
        elif '综合匹配度' in h_str:
            base_width = max(base_width, 12)
        elif '优先级' in h_str:
            base_width = max(base_width, 8)
        elif '处理动作' in h_str:
            base_width = max(base_width, 18)
        elif '序号' in h_str:
            base_width = max(base_width, 6)
        elif '性别' in h_str:
            base_width = max(base_width, 6)
        elif '学历' in h_str:
            base_width = max(base_width, 12)
        elif '期望月薪' in h_str:
            base_width = max(base_width, 10)
        elif '意向' in h_str or '擅长' in h_str:
            base_width = max(base_width, 25)
        elif '核心技能' in h_str or '工具' in h_str:
            base_width = max(base_width, 35)
        elif '核心亮点' in h_str:
            base_width = max(base_width, 45)
        elif '主要差距' in h_str:
            base_width = max(base_width, 40)
        elif '教育背景' in h_str:
            base_width = max(base_width, 40)
        elif '前期信息' in h_str:
            base_width = max(base_width, 30)
        else:
            base_width = max(base_width, 10)
        
        base_widths.append(base_width)
    
    for row in data_rows:
        for i, cell in enumerate(row):
            if i < len(base_widths):
                cell_str = str(cell)
                chinese_count = sum(1 for c in cell_str if '\u4e00' <= c <= '\u9fff')
                english_count = len(cell_str) - chinese_count
                cell_width = chinese_count * 1.5 + english_count * 0.9
                
                if cell_width > base_widths[i]:
                    base_widths[i] = cell_width
    
    return [max(8, min(w, 60)) for w in base_widths]


def apply_header_style(ws, headers):
    """
    应用表头样式
    
    为表头行应用以下样式：
    - 字体：微软雅黑、加粗、黑色、11号
    - 填充：浅绿色背景（兼容手机Excel应用）
    - 对齐：居中对齐、自动换行
    - 边框：细边框
    - 文字颜色：白色
    
    Args:
        ws: Worksheet对象
        headers: 表头列表
    """
    header_font = Font(bold=True, color='000000', size=11, name='微软雅黑')
    header_fill = PatternFill(start_color='98D7B6', end_color='98D7B6', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border


def apply_data_style(ws, row_num, row_data):
    """
    应用数据行样式
    
    为数据行应用以下样式：
    - 对齐：左对齐（文本）/居中对齐（数字、匹配度、优先级）、垂直居中、自动换行
    - 边框：细边框
    - 奇偶行着色：奇数行白色背景、偶数行浅灰色背景（条纹效果）
    - 优先级着色：根据优先级等级为优先级列着色（P0深绿色、P1深黄色、P2深橙色、P3灰色）
    - 匹配度着色：根据匹配度百分比着色（80%以上绿色、60-80%黄色、60%以下红色）
    
    Args:
        ws: Worksheet对象
        row_num: 行号
        row_data: 数据行列表
    """
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    left_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    priority_fills = {
        'P0': PatternFill(start_color='548235', end_color='548235', fill_type='solid'),
        'P1': PatternFill(start_color='BF9000', end_color='BF9000', fill_type='solid'),
        'P2': PatternFill(start_color='C00000', end_color='C00000', fill_type='solid'),
        'P3': PatternFill(start_color='70AD47', end_color='70AD47', fill_type='solid')
    }
    
    priority_fonts = {
        'P0': Font(bold=True, color='FFFFFF', size=11),
        'P1': Font(bold=True, color='FFFFFF', size=11),
        'P2': Font(bold=True, color='FFFFFF', size=11),
        'P3': Font(bold=True, color='FFFFFF', size=11)
    }
    
    match_score_col = -1
    priority_col = -1
    
    headers = [ws.cell(row=1, column=col).value for col in range(1, ws.max_column + 1)]
    if '综合匹配度' in headers:
        match_score_col = headers.index('综合匹配度') + 1
    if '优先级' in headers:
        priority_col = headers.index('优先级') + 1
    
    for col, cell_value in enumerate(row_data, 1):
        cell = ws.cell(row=row_num, column=col, value=cell_value)
        cell.border = thin_border
        
        if col == priority_col:
            cell.alignment = center_alignment
            if cell_value in priority_fills:
                cell.fill = priority_fills[cell_value]
                cell.font = priority_fonts[cell_value]
        elif col == match_score_col:
            cell.alignment = center_alignment
            cell.font = Font(bold=True, size=11)
            try:
                score = int(str(cell_value).replace('%', ''))
                if score >= 80:
                    cell.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
                    cell.font = Font(bold=True, color='006100', size=11)
                elif score >= 60:
                    cell.fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
                    cell.font = Font(bold=True, color='734F00', size=11)
                else:
                    cell.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
                    cell.font = Font(bold=True, color='9C0006', size=11)
            except:
                cell.fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
        elif str(cell_value).isdigit() or (isinstance(cell_value, (int, float)) and not isinstance(cell_value, bool)):
            cell.alignment = center_alignment
            cell.font = Font(size=11)
        else:
            cell.alignment = left_alignment
            cell.font = Font(size=11)
        
        if row_num % 2 == 0:
            if cell_value not in priority_fills or col != priority_col:
                current_fill = cell.fill
                if current_fill.start_color.rgb == '00000000' or current_fill.patternType is None:
                    cell.fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')


def write_position_excel(position_key, candidates, output_dir=None, dimensions=None):
    """
    为单个岗位写入Excel文件
    
    创建一个包含该岗位所有候选人评估结果的Excel文件，使用模板文件保持格式一致性。
    支持动态评估维度字段，在"综合匹配度"字段前插入各维度匹配度。
    
    Args:
        position_key: 岗位类型关键字
        candidates: 候选人列表（已排序）
        output_dir: 输出目录（可选）
        dimensions: 评估维度列表（可选），用于动态生成维度字段
        
    Returns:
        str: 生成的Excel文件路径
    """
    if output_dir is None:
        output_dir = create_output_directory()
    
    filename = f"{position_key}岗位候选人评估结果_{get_timestamp()}.xlsx"
    filepath = os.path.join(output_dir, filename)
    
    if os.path.exists(OUTPUT_TEMPLATE_PATH):
        wb = load_workbook(OUTPUT_TEMPLATE_PATH)
        ws = wb.active
        ws.title = f"{position_key}岗位"
        for row in range(1, ws.max_row + 1):
            for col in range(1, ws.max_column + 1):
                ws.cell(row=row, column=col, value=None)
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = f"{position_key}岗位"
    
    base_headers = OUTPUT_COLUMNS.copy()
    
    match_score_index = base_headers.index('综合匹配度') if '综合匹配度' in base_headers else len(base_headers)
    
    dimension_headers = []
    if dimensions:
        for dim in dimensions:
            dim_id = dim.get('id', '')
            dim_name = dim.get('name', '')
            dim_weight = dim.get('weight', 0)
            dimension_headers.append(f"{dim_id}-{dim_name}({dim_weight}%)")
    
    headers = base_headers[:match_score_index] + dimension_headers + base_headers[match_score_index:]
    
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)
    
    apply_header_style(ws, headers)
    
    degree_order = ['博士', '硕士', '本科', '大专', '专科', '高中', '中专']
    data_rows = []
    for candidate in candidates:
        education_details = candidate.get('education_details', [])
        
        if isinstance(education_details, str):
            details_str = education_details.strip()
        elif isinstance(education_details, list) and education_details:
            highest_edu = None
            highest_degree_index = len(degree_order)
            for edu in education_details:
                if isinstance(edu, dict):
                    degree = edu.get('degree', '')
                    if degree in degree_order:
                        index = degree_order.index(degree)
                        if index < highest_degree_index:
                            highest_degree_index = index
                            highest_edu = edu
            if highest_edu is None:
                highest_edu = education_details[-1]
            if isinstance(highest_edu, dict):
                details_str = f"{highest_edu.get('start_year', '')}-{highest_edu.get('end_year', '')} {highest_edu.get('school', '')} {highest_edu.get('major', '')} {highest_edu.get('degree', '')}".strip()
            else:
                details_str = str(highest_edu).strip()
        else:
            details_str = ''
        
        base_row = [
            candidate.get('rank', ''),
            candidate.get('name', ''),
            candidate.get('phone', ''),
            candidate.get('gender', ''),
            candidate.get('age', ''),
            candidate.get('education', ''),
            details_str,
            candidate.get('experience', ''),
            candidate.get('skills', ''),
            candidate.get('core_strengths', ''),
            candidate.get('main_risks', ''),
            candidate.get('intention_modules', ''),
            candidate.get('position', ''),
            candidate.get('expected_salary', ''),
            candidate.get('preliminary_info', ''),
            f"{candidate.get('match_score', 0)}%",
            candidate.get('priority', ''),
            candidate.get('suggested_action', '')
        ]
        
        dimension_scores = candidate.get('dimension_scores', {})
        dimension_details = candidate.get('dimension_details', {})
        
        dimension_values = []
        if dimensions:
            for dim in dimensions:
                dim_id = dim.get('id', '')
                rating = dimension_scores.get(dim_id, '')
                if rating != '':
                    dim_detail = dimension_details.get(dim_id, {})
                    if isinstance(dim_detail, dict):
                        weighted_score = dim_detail.get('weighted_score', '')
                        if weighted_score != '':
                            dimension_values.append(f"{rating}/5 ({weighted_score}%)")
                        else:
                            dimension_values.append(f"{rating}/5")
                    else:
                        dimension_values.append(f"{rating}/5")
                else:
                    dimension_values.append('')
        
        row = base_row[:match_score_index] + dimension_values + base_row[match_score_index:]
        data_rows.append(row)
    
    for row_num, row_data in enumerate(data_rows, 2):
        apply_data_style(ws, row_num, row_data)
    
    column_widths = get_column_widths(headers, data_rows)
    for col, width in enumerate(column_widths, 1):
        col_letter = ws.cell(row=1, column=col).column_letter
        ws.column_dimensions[col_letter].width = width
    
    ws.row_dimensions[1].height = 28
    
    max_content_length = 0
    for row in data_rows:
        for cell in row:
            cell_length = len(str(cell))
            if cell_length > max_content_length:
                max_content_length = cell_length
    
    base_row_height = 20
    if max_content_length > 50:
        base_row_height = 25
    if max_content_length > 100:
        base_row_height = 30
    if max_content_length > 200:
        base_row_height = 35
    
    for row_num in range(2, len(data_rows) + 2):
        ws.row_dimensions[row_num].height = base_row_height
    
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            wb.save(filepath)
            logger.info(f"成功生成Excel文件: {filepath}")
            return filepath
        except PermissionError:
            if attempt < max_retries - 1:
                logger.warning(f"文件权限不足，重试第{attempt+2}/{max_retries}次...")
                time.sleep(1)
            else:
                logger.error(f"文件权限不足，无法保存: {filepath}")
                raise
    
    return filepath


def write_all_positions_excel(processed_results, output_dir=None, criteria_dict=None):
    """
    为所有岗位写入Excel文件
    
    遍历处理后的评估结果，为每个岗位生成独立的Excel文件。
    
    Args:
        processed_results: 处理后的评估结果
        output_dir: 输出目录（可选）
        criteria_dict: 各岗位的评估标准字典（可选），用于获取维度信息
        
    Returns:
        dict: 各岗位生成的Excel文件路径（岗位类型 -> 文件路径）
    """
    if output_dir is None:
        output_dir = create_output_directory()
    
    file_paths = {}
    
    for position_key, data in processed_results.items():
        candidates = data['sorted_list']
        dimensions = None
        if criteria_dict and position_key in criteria_dict:
            dimensions = criteria_dict[position_key].get('dimensions', None)
        filepath = write_position_excel(position_key, candidates, output_dir, dimensions)
        file_paths[position_key] = filepath
    
    return file_paths


def write_summary_excel(processed_results, output_dir=None):
    """
    生成汇总Excel文件，包含所有岗位的评估结果
    
    创建一个包含多个工作表的Excel文件：
    1. 评估汇总：各岗位的评估统计（总人数、各优先级人数）
    2. 各岗位工作表：该岗位所有候选人的详细评估结果（使用新字段）
    
    Args:
        processed_results: 处理后的评估结果
        output_dir: 输出目录（可选）
        
    Returns:
        str: 生成的汇总Excel文件路径
    """
    if output_dir is None:
        output_dir = create_output_directory()
    
    filename = f"候选人评估汇总报告_{get_timestamp()}.xlsx"
    filepath = os.path.join(output_dir, filename)
    
    wb = Workbook()
    
    summary_ws = wb.active
    summary_ws.title = "评估汇总"
    
    summary_data = [
        ["岗位", "总人数", "P0(优先推荐)", "P1(推荐)", "P2(备选)", "P3(暂不推荐)"],
    ]
    
    total_row = ["总计", 0, 0, 0, 0, 0]
    
    for position_key, data in processed_results.items():
        dist = data['distribution']
        summary_data.append([
            position_key,
            dist['total'],
            dist['P0'],
            dist['P1'],
            dist['P2'],
            dist['P3']
        ])
        total_row[1] += dist['total']
        total_row[2] += dist['P0']
        total_row[3] += dist['P1']
        total_row[4] += dist['P2']
        total_row[5] += dist['P3']
    
    summary_data.append(total_row)
    
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    for row_num, row_data in enumerate(summary_data, 1):
        for col_num, cell_value in enumerate(row_data, 1):
            cell = summary_ws.cell(row=row_num, column=col_num, value=cell_value)
            cell.border = thin_border
            
            if row_num == 1:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            else:
                cell.alignment = Alignment(horizontal='center', vertical='center')
    
    for col in range(1, len(summary_data[0]) + 1):
        summary_ws.column_dimensions[chr(64 + col)].width = 15
    
    for position_key, data in processed_results.items():
        ws = wb.create_sheet(title=f"{position_key}岗位")
        
        headers = OUTPUT_COLUMNS
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        candidates = data['sorted_list']
        data_rows = []
        
        for candidate in candidates:
            education_details = candidate.get('education_details', [])
            details_str = '\n'.join([
                f"{e.get('start_year', '')}-{e.get('end_year', '')} {e.get('school', '')} {e.get('major', '')} {e.get('degree', '')}"
                for e in education_details
            ]).strip()
            
            row = [
                candidate.get('rank', ''),
                candidate.get('name', ''),
                candidate.get('phone', ''),
                candidate.get('gender', ''),
                candidate.get('age', ''),
                candidate.get('education', ''),
                candidate.get('first_degree', ''),
                candidate.get('first_degree_school', ''),
                candidate.get('first_degree_major', ''),
                details_str,
                candidate.get('experience', ''),
                candidate.get('skills', ''),
                candidate.get('core_strengths', ''),
                candidate.get('main_risks', ''),
                candidate.get('intention_modules', ''),
                candidate.get('position', ''),
                candidate.get('preliminary_info', ''),
                f"{candidate.get('match_score', 0)}%",
                candidate.get('priority', ''),
                candidate.get('rating_reason', ''),
                candidate.get('suggested_action', '')
            ]
            data_rows.append(row)
        
        for row_num, row_data in enumerate(data_rows, 2):
            for col_num, cell_value in enumerate(row_data, 1):
                cell = ws.cell(row=row_num, column=col_num, value=cell_value)
                cell.border = thin_border
                cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        
        column_widths = get_column_widths(headers, data_rows)
        for col, width in enumerate(column_widths, 1):
            col_letter = ws.cell(row=1, column=col).column_letter
            ws.column_dimensions[col_letter].width = width
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            wb.save(filepath)
            logger.info(f"成功生成汇总Excel文件: {filepath}")
            return filepath
        except PermissionError:
            if attempt < max_retries - 1:
                logger.warning(f"文件权限不足，重试第{attempt+2}/{max_retries}次...")
                time.sleep(1)
            else:
                logger.error(f"文件权限不足，无法保存: {filepath}")
                raise
    
    return filepath
