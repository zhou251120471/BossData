"""
简历智能评估系统 - 评估标准解析模块

该模块负责解析评估标准文件，支持.xlsx（Excel）和.docx（Word）两种格式，提取评估维度和优先级等级标准。

核心功能：
1. Excel文件解析：使用openpyxl库读取Excel文件中的工作表数据
2. Word文件解析：使用python-docx库读取Word文件中的表格数据
3. 评估维度提取：从表格中识别并提取各评估维度的名称、权重和标准
4. 优先级等级提取：从表格中识别并提取各优先级等级的定义和分数范围
5. 标准格式化：将提取的评估标准格式化为便于大模型理解的文本格式
6. 自动发现：支持自动扫描评估标准目录，发现新的岗位评估标准

使用依赖：
- openpyxl：Excel文件解析
- python-docx：Word文件解析
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


def _parse_evaluation_rows(rows):
    """
    通用表格行解析函数
    
    根据表头内容判断表格类型，提取评估维度和优先级等级标准。
    
    Args:
        rows: 表格行数据列表，每行是一个单元格列表
        
    Returns:
        dict: 包含dimensions(评估维度)和priority_levels(优先级等级)的字典
    """
    result = {
        'dimensions': [],
        'priority_levels': []
    }
    
    if len(rows) < 2:
        return result
    
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
    
    return result


def parse_evaluation_excel(excel_path):
    """
    解析评估标准Excel文件（.xlsx格式），提取评估维度和优先级等级标准
    
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
            
            sheet_result = _parse_evaluation_rows(rows)
            result['dimensions'].extend(sheet_result['dimensions'])
            result['priority_levels'].extend(sheet_result['priority_levels'])
        
        total_weight = sum(dim.get('weight', 0) for dim in result['dimensions'])
        if result['dimensions'] and total_weight != 100:
            logger.warning(f"评估维度权重总和不是100%: {total_weight}%, 文件: {excel_path}")
        
        logger.info(f"成功解析评估标准Excel文件: {excel_path}")
        logger.info(f"  - 评估维度: {len(result['dimensions'])}个, 权重总和: {total_weight}%")
        logger.info(f"  - 优先级等级: {len(result['priority_levels'])}个")
        
    except Exception as e:
        logger.error(f"解析评估标准Excel文件失败: {excel_path}, 错误: {str(e)}")
    
    return result


def parse_evaluation_docx(docx_path):
    """
    解析评估标准Word文件（.docx格式），提取评估维度和优先级等级标准
    
    遍历Word文件中的所有表格，根据表头内容判断表格类型：
    1. 评估维度表格：表头包含"评估维度"关键字
    2. 优先级等级表格：表头包含"等级"或"优先级"关键字
    
    注意事项：
    - 优先级等级表格需满足行数<=6且尚未提取过优先级等级的条件
    - 优先级等级必须为P0/P1/P2/P3之一才会被提取
    
    Args:
        docx_path: 评估标准Word文件的路径
        
    Returns:
        dict: 包含dimensions(评估维度)和priority_levels(优先级等级)的字典
    """
    result = {
        'dimensions': [],
        'priority_levels': []
    }
    
    if not os.path.exists(docx_path):
        logger.error(f"评估标准Word文件不存在: {docx_path}")
        return result
    
    try:
        from docx import Document
        
        doc = Document(docx_path)
        
        for table in doc.tables:
            rows = []
            for row in table.rows:
                cells = [cell.text.strip() if cell.text else '' for cell in row.cells]
                if any(cells):
                    rows.append(cells)
            
            table_result = _parse_evaluation_rows(rows)
            result['dimensions'].extend(table_result['dimensions'])
            result['priority_levels'].extend(table_result['priority_levels'])
        
        total_weight = sum(dim.get('weight', 0) for dim in result['dimensions'])
        if result['dimensions'] and total_weight != 100:
            logger.warning(f"评估维度权重总和不是100%: {total_weight}%, 文件: {docx_path}")
        
        logger.info(f"成功解析评估标准Word文件: {docx_path}")
        logger.info(f"  - 评估维度: {len(result['dimensions'])}个, 权重总和: {total_weight}%")
        logger.info(f"  - 优先级等级: {len(result['priority_levels'])}个")
        
    except Exception as e:
        logger.error(f"解析评估标准Word文件失败: {docx_path}, 错误: {str(e)}")
    
    return result


def parse_evaluation_doc(doc_path):
    """
    解析评估标准Word文件（.doc格式），提取评估维度和优先级等级标准
    
    使用pywin32库通过COM接口调用Microsoft Word来读取.doc文件中的表格数据。
    遍历Word文件中的所有表格，根据表头内容判断表格类型：
    1. 评估维度表格：表头包含"评估维度"关键字
    2. 优先级等级表格：表头包含"等级"或"优先级"关键字
    
    注意事项：
    - 需要在Windows系统上运行，且已安装Microsoft Word
    - 如果COM调用失败，会尝试使用antiword（Linux/Unix系统）作为备用方案
    - 优先级等级表格需满足行数<=6且尚未提取过优先级等级的条件
    - 优先级等级必须为P0/P1/P2/P3之一才会被提取
    
    Args:
        doc_path: 评估标准Word文件（.doc格式）的路径
        
    Returns:
        dict: 包含dimensions(评估维度)和priority_levels(优先级等级)的字典
    """
    result = {
        'dimensions': [],
        'priority_levels': []
    }
    
    if not os.path.exists(doc_path):
        logger.error(f"评估标准Word文件不存在: {doc_path}")
        return result
    
    try:
        import win32com.client
        import pythoncom
        
        pythoncom.CoInitialize()
        
        word = win32com.client.Dispatch('Word.Application')
        word.Visible = False
        
        try:
            doc = word.Documents.Open(doc_path)
            
            for table in doc.Tables:
                rows = []
                for i in range(1, table.Rows.Count + 1):
                    cells = []
                    for j in range(1, table.Columns.Count + 1):
                        try:
                            cell_text = table.Cell(i, j).Range.Text.strip()
                            cell_text = cell_text.replace('\r', '').replace('\x07', '')
                            cells.append(cell_text)
                        except:
                            cells.append('')
                    if any(cells):
                        rows.append(cells)
                
                table_result = _parse_evaluation_rows(rows)
                result['dimensions'].extend(table_result['dimensions'])
                result['priority_levels'].extend(table_result['priority_levels'])
            
            doc.Close(SaveChanges=False)
            
            total_weight = sum(dim.get('weight', 0) for dim in result['dimensions'])
            if result['dimensions'] and total_weight != 100:
                logger.warning(f"评估维度权重总和不是100%: {total_weight}%, 文件: {doc_path}")
            
            logger.info(f"成功解析评估标准Word文件(.doc): {doc_path}")
            logger.info(f"  - 评估维度: {len(result['dimensions'])}个, 权重总和: {total_weight}%")
            logger.info(f"  - 优先级等级: {len(result['priority_levels'])}个")
            
        finally:
            word.Quit()
            pythoncom.CoUninitialize()
        
    except Exception as e:
        logger.error(f"解析评估标准Word文件失败(.doc): {doc_path}, 错误: {str(e)}")
        logger.info("尝试使用antiword作为备用方案...")
        
        try:
            import subprocess
            result = subprocess.run(
                ['antiword', doc_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                logger.info("antiword解析成功，但仅提取了文本内容，表格结构可能丢失")
            
        except:
            logger.error("antiword也不可用，请将.doc文件转换为.docx格式后再使用")
    
    return result


def discover_evaluation_docs():
    """
    自动发现所有评估标准文件
    
    扫描ASSESSMENT_CRITERIA_PATH目录下的所有Excel和Word文件（支持.xlsx、.docx、.doc格式）。
    返回文件名到文件路径的映射。
    
    Returns:
        dict: 以文件名为键，文件路径为值的字典
    """
    evaluation_docs = {}
    
    if not os.path.exists(ASSESSMENT_CRITERIA_PATH):
        logger.error(f"评估标准目录不存在: {ASSESSMENT_CRITERIA_PATH}")
        return evaluation_docs
    
    try:
        for filename in os.listdir(ASSESSMENT_CRITERIA_PATH):
            if filename.lower().endswith('.xlsx') or filename.lower().endswith('.docx') or filename.lower().endswith('.doc'):
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
    
    使用LLM智能匹配找到对应的评估标准文件，然后根据文件扩展名选择正确的解析函数：
    - .xlsx 文件：使用 parse_evaluation_excel() 解析（openpyxl库）
    - .docx 文件：使用 parse_evaluation_docx() 解析（python-docx库）
    - .doc 文件：使用 parse_evaluation_doc() 解析（pywin32 COM接口调用Microsoft Word）
    
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
    
    file_path = match_eval_doc(position_key)
    
    if file_path and os.path.exists(file_path):
        # 根据文件扩展名选择解析函数
        if file_path.lower().endswith('.xlsx'):
            criteria = parse_evaluation_excel(file_path)
        elif file_path.lower().endswith('.docx'):
            criteria = parse_evaluation_docx(file_path)
        elif file_path.lower().endswith('.doc'):
            criteria = parse_evaluation_doc(file_path)
        else:
            logger.warning(f"不支持的评估标准文件格式: {file_path}")
            criteria = {'dimensions': [], 'priority_levels': []}
        
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


def extract_text_from_doc(doc_path):
    """
    从文档中提取纯文本内容
    
    支持Excel(.xlsx)和Word(.docx/.doc)格式，将文档内容转换为纯文本，
    便于大模型处理。
    
    Args:
        doc_path: 文档文件路径
        
    Returns:
        str: 提取的文本内容，失败返回空字符串
    """
    if not os.path.exists(doc_path):
        logger.error(f"文档文件不存在: {doc_path}")
        return ""
    
    try:
        if doc_path.lower().endswith('.xlsx'):
            wb = load_workbook(doc_path, data_only=True)
            text_parts = []
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                for row in sheet.iter_rows(values_only=True):
                    cells = [str(cell).strip() for cell in row if cell is not None]
                    if any(cells):
                        text_parts.append(' | '.join(cells))
            return '\n'.join(text_parts)
        
        elif doc_path.lower().endswith('.docx'):
            from docx import Document
            doc = Document(doc_path)
            text_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text]
                    if any(cells):
                        text_parts.append(' | '.join(cells))
            return '\n'.join(text_parts)
        
        elif doc_path.lower().endswith('.doc'):
            try:
                import win32com.client
                import pythoncom
                pythoncom.CoInitialize()
                word = win32com.client.Dispatch('Word.Application')
                word.Visible = False
                try:
                    doc = word.Documents.Open(doc_path)
                    text = doc.Content.Text
                    doc.Close(SaveChanges=False)
                    return text.strip()
                finally:
                    word.Quit()
                    pythoncom.CoUninitialize()
            except Exception as e:
                logger.warning(f"使用COM接口读取.doc文件失败: {e}")
                return ""
        
        else:
            logger.warning(f"不支持的文件格式: {doc_path}")
            return ""
            
    except Exception as e:
        logger.error(f"提取文档文本失败: {doc_path}, 错误: {str(e)}")
        return ""


def get_evaluation_criteria_with_llm(position_key):
    """
    使用大模型提取评估标准
    
    调用大模型从评估标准文档中提取结构化信息，包括评估维度和优先级等级。
    如果大模型调用失败，回退到传统的文档解析方法。
    
    Args:
        position_key: 岗位类型关键字
        
    Returns:
        dict: 包含dimensions和priority_levels的字典
    """
    if position_key in _criteria_cache:
        return _criteria_cache[position_key]
    
    from utils.resource_manager import match_eval_doc
    
    file_path = match_eval_doc(position_key)
    
    if file_path and os.path.exists(file_path):
        try:
            from llm.criteria_extractor import extract_criteria_with_llm as llm_extract
            
            doc_text = extract_text_from_doc(file_path)
            
            llm_result = llm_extract(doc_text, position_key)
            
            if llm_result:
                _criteria_cache[position_key] = llm_result
                total_weight = sum(dim.get('weight', 0) for dim in llm_result.get('dimensions', []))
                logger.info(f"LLM评估标准提取成功，岗位: {position_key}，维度数: {len(llm_result.get('dimensions', []))}，权重总和: {total_weight}%")
                return llm_result
            
            logger.info("LLM评估标准提取失败，回退到传统方法")
            
        except Exception as e:
            logger.warning(f"调用LLM提取评估标准失败: {str(e)}，回退到传统方法")
    
    return get_evaluation_criteria(position_key)


def get_all_evaluation_criteria_with_llm():
    """
    使用大模型获取所有岗位的评估标准
    
    自动扫描评估标准目录发现所有岗位，逐个调用get_evaluation_criteria_with_llm函数，
    将结果汇总到字典中返回。
    
    Returns:
        dict: 以岗位类型为键，评估标准为值的字典
    """
    all_criteria = {}
    evaluation_docs = discover_evaluation_docs()
    
    for position_key in evaluation_docs.keys():
        all_criteria[position_key] = get_evaluation_criteria_with_llm(position_key)
    
    return all_criteria