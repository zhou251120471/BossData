"""
简历智能评估系统 - 简历读取模块

该模块负责从PDF文件中提取简历内容，并解析候选人信息。

核心功能：
1. PDF文本提取：优先使用PyMuPDF（fitz），当PyMuPDF不可用时回退到PyPDF2
2. 文件名解析：从简历文件名中提取姓名、岗位、工作年限等基本信息
3. 简历内容解析：从提取的文本中识别学历、技能、项目经验等详细信息
4. 批量读取：按岗位分类读取所有简历文件（支持自动发现新岗位）

使用依赖：
- PyMuPDF（fitz）：PDF文件解析（优先）
- PyPDF2：PDF文件解析（备选）
- re：正则表达式匹配
- os：文件系统操作
- logging：日志记录
"""

import os
import re
import logging

logger = logging.getLogger(__name__)

from PyPDF2 import PdfReader

try:
    import fitz
    HAS_FITZ = True
    logger.info("成功导入PyMuPDF（fitz），将优先使用该库解析PDF")
except ImportError:
    HAS_FITZ = False
    logger.warning("PyMuPDF（fitz）未安装，将使用PyPDF2解析PDF")

from config import RESUMES_PATH


def extract_text_from_pdf(pdf_path):
    """
    从PDF文件中提取文本内容
    
    优先使用PyMuPDF（fitz）库解析PDF，因其对中文编码和复杂格式支持更好；
    当PyMuPDF不可用或解析失败时，回退到PyPDF2库。
    若解析过程中发生异常（如文件损坏、加密等），记录错误日志并返回空字符串。
    
    Args:
        pdf_path: PDF文件的完整路径
        
    Returns:
        str: 提取的文本内容，如果解析失败返回空字符串
    """
    if HAS_FITZ:
        try:
            doc = fitz.open(pdf_path)
            text = ''
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    text += page_text
            doc.close()
            return text.strip()
        except Exception as e:
            logger.warning(f"PyMuPDF解析PDF失败: {pdf_path}, 错误: {str(e)}，尝试使用PyPDF2")
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            text = ''
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
            return text.strip()
    except Exception as e:
        logger.error(f"解析PDF文件失败: {pdf_path}, 错误: {str(e)}")
        return ''


def parse_filename(filename):
    """
    从文件名中解析候选人信息（姓名、岗位、年限、期望薪资）
    
    支持多种文件名格式：
    1. 标准格式：【前端开发工程师_北京 8-12K】于宗源 4年.pdf
    2. 简化格式：于宗源 4年.pdf
    3. 基础格式：张三.pdf
    
    使用正则表达式匹配文件名中的关键信息，若匹配失败则返回文件名（不含扩展名）作为姓名。
    
    Args:
        filename: 简历文件名
        
    Returns:
        dict: 包含name(姓名), position(岗位), experience(年限), expected_salary(期望薪资)的字典
    """
    result = {
        'name': '',
        'position': '',
        'experience': '',
        'expected_salary': ''
    }
    
    try:
        name_pattern = re.compile(r'【(.+?)】(.+?)\s*(\d+年|10年以上)')
        match = name_pattern.search(filename)
        if match:
            position_full = match.group(1).strip()
            salary_pattern = re.compile(r'(\d+[-~]\d+[Kk])')
            salary_match = salary_pattern.search(position_full)
            if salary_match:
                result['expected_salary'] = salary_match.group(1).upper()
                result['position'] = position_full.replace(salary_match.group(1), '').strip()
            else:
                result['position'] = position_full
            result['name'] = match.group(2).strip()
            result['experience'] = match.group(3).strip()
        else:
            name_only_pattern = re.compile(r'(.+?)\s*(\d+年|10年以上)')
            match2 = name_only_pattern.search(filename)
            if match2:
                result['name'] = match2.group(1).strip().replace('【', '').replace('】', '')
                result['experience'] = match2.group(2).strip()
            else:
                result['name'] = os.path.splitext(filename)[0].strip()
    except Exception as e:
        logger.error(f"解析文件名失败: {filename}, 错误: {str(e)}")
        result['name'] = os.path.splitext(filename)[0].strip()
    
    return result


def extract_candidate_info_from_text(text):
    """
    从简历文本中提取候选人详细信息
    
    使用正则表达式从简历文本中识别并提取以下信息：
    - 学历：匹配本科、硕士、大专等学历关键词
    - 教育背景详情：提取学校、专业、学位、起止年份
    - 技能：匹配技能、专业技能、核心技能等字段
    - 项目经验：匹配项目经验、工作经历等字段
    - 个人简介：匹配个人简介、自我评价等字段
    
    Args:
        text: 简历文本内容
        
    Returns:
        dict: 包含学历、技能等信息的字典
    """
    info = {
        'education': '',
        'education_details': [],
        'skills': '',
        'projects': '',
        'summary': '',
        'phone': '',
        'gender': '',
        'age': ''
    }
    
    try:
        phone_patterns = [
            r'(?:手机|电话|联系方式|手机号|联系电话)\s*[:：]\s*(1[3-9]\d{9})',
            r'(1[3-9]\d{9})',
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                info['phone'] = match.group(1).strip()
                break
        
        gender_patterns = [
            r'(?:性别)\s*[:：]\s*(男|女)',
            r'\b(男|女)\b',
        ]
        
        for pattern in gender_patterns:
            match = re.search(pattern, text)
            if match:
                info['gender'] = match.group(1).strip()
                break
        
        age_patterns = [
            r'(?:年龄|岁数)\s*[:：]\s*(\d{1,2})\s*岁?',
            r'(\d{1,2})\s*岁',
            r'(?:出生|生日|出生日期)\s*[:：]\s*(\d{4})\s*年',
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, text)
            if match:
                value = match.group(1).strip()
                if len(value) == 4 and int(value) >= 1960:
                    import datetime
                    info['age'] = str(datetime.datetime.now().year - int(value))
                else:
                    info['age'] = value
                break
        
        lines = text.split('\n')
        edu_section_start = -1
        edu_section_end = -1
        
        for i, line in enumerate(lines):
            if any(keyword in line for keyword in ['教育经历', '教育背景', '学历背景']):
                edu_section_start = i + 1
                continue
            
            if edu_section_start > 0 and edu_section_end == -1:
                if line.strip() and any(keyword in line for keyword in ['工作经历', '项目经验', '自我评价', '个人简介', '技能', '专业技能', '工作经验']):
                    edu_section_end = i
                    break
                if i - edu_section_start > 15:
                    edu_section_end = i
                    break
        
        if edu_section_end == -1 and edu_section_start > 0:
            edu_section_end = min(edu_section_start + 15, len(lines))
        
        if edu_section_start > 0:
            edu_lines = lines[edu_section_start:edu_section_end]
            
            edu_text_parts = []
            for line in edu_lines:
                line = line.strip()
                if not line or len(line) < 2:
                    continue
                
                clean_line = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9（）()-~至～]', '', line)
                if not clean_line:
                    continue
                
                if re.search(r'[a-f0-9]{8,}', clean_line):
                    continue
                
                if '项目名称' in clean_line or '技术栈' in clean_line or '项目介绍' in clean_line:
                    break
                
                has_edu_keyword = ('大学' in clean_line or '学院' in clean_line or \
                                   '本科' in clean_line or '硕士' in clean_line or '大专' in clean_line or \
                                   re.search(r'\d{4}', clean_line) or '专业' in clean_line or '系' in clean_line)
                
                if has_edu_keyword:
                    if '大学' in clean_line or '学院' in clean_line:
                        if len(clean_line) > 20 and ('大学' in clean_line or '学院' in clean_line):
                            school_end = clean_line.find('大学') + 2
                            if school_end <= 1:
                                school_end = clean_line.find('学院') + 2
                            if school_end > 1:
                                school_part = clean_line[:school_end].strip()
                                remaining = clean_line[school_end:].strip()
                                edu_text_parts.append(school_part)
                                if remaining:
                                    edu_text_parts.append(remaining)
                                continue
                    edu_text_parts.append(clean_line)
                    
                    degree_match = re.search(r'(本科|硕士|大专|专科|博士)', clean_line)
                    if degree_match and not info['education']:
                        info['education'] = degree_match.group(1)
            
            if edu_text_parts:
                info['education_details'] = [{'text': '\n'.join(edu_text_parts)}]
        
        if not info['education_details']:
            edu_details_patterns = [
                r'(\d{4})\s*[-~至～]\s*(\d{4}|\d{2})\s*([^\n\r]+?大学|[^\n\r]+?学院)\s*([^\n\r]+)',
                r'([^\n\r]+?大学|[^\n\r]+?学院)\s*([^\n\r]+?)\s*(本科|硕士|大专|专科|博士)',
                r'(本科|硕士|大专|专科|博士)\s*[:：]\s*([^\n\r]+?大学|[^\n\r]+?学院)\s*([^\n\r]+?)',
            ]
            
            for pattern in edu_details_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    edu_detail = {
                        'start_year': match[0].strip() if len(match) > 0 else '',
                        'end_year': match[1].strip() if len(match) > 1 else '',
                        'school': match[2].strip() if len(match) > 2 else '',
                        'major': match[3].strip() if len(match) > 3 else '',
                        'degree': match[4].strip() if len(match) > 4 else ''
                    }
                    
                    if len(edu_detail['start_year']) == 4:
                        pass
                    elif len(edu_detail['start_year']) == 2:
                        edu_detail['start_year'] = '20' + edu_detail['start_year']
                    else:
                        edu_detail['start_year'] = ''
                    
                    if len(edu_detail['end_year']) == 4:
                        pass
                    elif len(edu_detail['end_year']) == 2:
                        edu_detail['end_year'] = '20' + edu_detail['end_year']
                    else:
                        edu_detail['end_year'] = ''
                    
                    if edu_detail['school'] or edu_detail['degree']:
                        info['education_details'].append(edu_detail)
                        if not info['education'] and edu_detail['degree']:
                            info['education'] = edu_detail['degree']
        
        if not info['education']:
            edu_only_patterns = [
                r'学历\s*[:：]\s*(本科|硕士|大专|专科|博士)',
                r'(全日制|统招)\s*(本科|硕士|大专)',
                r'\b(本科|硕士|大专|专科|博士)\b'
            ]
            for pattern in edu_only_patterns:
                match = re.search(pattern, text)
                if match:
                    info['education'] = match.group(1).strip()
                    break
        
        skill_patterns = [
            r'(技能|专业技能|核心技能|技术栈)\s*[:：]\s*([^\n\r]+)',
            r'熟练\s*(掌握|使用)\s*([^\n\r]+)',
            r'精通\s*([^\n\r]+)'
        ]
        
        skills_found = []
        for pattern in skill_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                skills_found.append(match[-1].strip())
        
        if skills_found:
            info['skills'] = '; '.join(skills_found[:5])
        
        project_pattern = r'(项目经验|工作经历|项目经历)\s*[:：]?\s*([\s\S]*?)(?=\n\n|\n---|\Z)'
        match = re.search(project_pattern, text)
        if match:
            info['projects'] = match.group(2).strip()[:500]
        
        summary_pattern = r'(个人简介|自我评价|个人总结)\s*[:：]?\s*([\s\S]*?)(?=\n\n|\Z)'
        match = re.search(summary_pattern, text)
        if match:
            info['summary'] = match.group(2).strip()[:300]
        
        if not info['summary']:
            info['summary'] = text[:500]
    
    except Exception as e:
        logger.error(f"提取候选人信息失败: {str(e)}")
    
    return info


def discover_positions():
    """
    自动发现所有岗位类型
    
    扫描RESUMES_PATH目录下的所有子目录，每个子目录代表一个岗位类型。
    返回原始目录名，不做映射处理。
    
    Returns:
        dict: 以目录名为键，目录路径为值的字典
    """
    position_dirs = {}
    
    if not os.path.exists(RESUMES_PATH):
        logger.error(f"简历根目录不存在: {RESUMES_PATH}")
        return position_dirs
    
    try:
        for item in os.listdir(RESUMES_PATH):
            item_path = os.path.join(RESUMES_PATH, item)
            if os.path.isdir(item_path):
                position_dirs[item] = item_path
                logger.info(f"发现简历目录: {item}")
        
        logger.info(f"共发现 {len(position_dirs)} 个简历目录")
    except Exception as e:
        logger.error(f"扫描简历目录失败: {str(e)}")
    
    return position_dirs


def get_position_key(dir_name):
    """
    从目录名称提取岗位标识
    
    通过移除后缀（如"人员的简历"、"简历"等）提取岗位关键词。
    
    Args:
        dir_name: 目录名称
        
    Returns:
        str: 岗位标识（如"前端"、"测试"、"UX"）
    """
    patterns = [
        r'(.+?)人员的简历',
        r'(.+?)的简历',
        r'(.+?)简历'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, dir_name)
        if match:
            return match.group(1).strip()
    
    return dir_name.strip()


def read_resumes_for_position(position_key, resume_dir=None):
    """
    读取指定岗位的所有简历
    
    根据岗位关键字查找对应的简历目录，遍历目录中的所有PDF文件，
    逐个解析文件名和PDF内容，构建候选人信息列表。
    
    Args:
        position_key: 岗位类型关键字
        resume_dir: 简历目录路径（可选，若不传则自动查找）
        
    Returns:
        list: 包含候选人信息的字典列表
    """
    candidates = []
    
    if resume_dir is None:
        position_dirs = discover_positions()
        resume_dir = position_dirs.get(position_key)
    
    if not resume_dir or not os.path.exists(resume_dir):
        logger.error(f"简历目录不存在: {resume_dir}")
        return candidates
    
    pdf_files = [f for f in os.listdir(resume_dir) if f.lower().endswith('.pdf')]
    
    logger.info(f"开始读取{position_key}岗位的简历，共{len(pdf_files)}份")
    
    for filename in pdf_files:
        pdf_path = os.path.join(resume_dir, filename)
        
        file_info = parse_filename(filename)
        
        text = extract_text_from_pdf(pdf_path)
        
        text_info = extract_candidate_info_from_text(text)
        
        candidate = {
            'filename': filename,
            'name': file_info['name'],
            'position': file_info['position'] or position_key,
            'experience': file_info['experience'],
            'expected_salary': file_info['expected_salary'],
            'education': text_info['education'],
            'education_details': text_info['education_details'],
            'skills': text_info['skills'],
            'projects': text_info['projects'],
            'summary': text_info['summary'],
            'phone': text_info['phone'],
            'gender': text_info['gender'],
            'age': text_info['age'],
            'full_text': text
        }
        
        candidates.append(candidate)
        logger.debug(f"已读取简历: {filename}")
    
    logger.info(f"完成{position_key}岗位简历读取，共{len(candidates)}份")
    
    return candidates


def get_all_resumes():
    """
    读取所有岗位的简历
    
    自动扫描简历目录发现所有岗位，逐个调用read_resumes_for_position函数，
    将结果汇总到字典中返回。支持任意数量的岗位类型。
    
    Returns:
        dict: 以岗位类型为键，候选人列表为值的字典
    """
    all_resumes = {}
    position_dirs = discover_positions()
    
    for position_key, resume_dir in position_dirs.items():
        all_resumes[position_key] = read_resumes_for_position(position_key, resume_dir)
    
    return all_resumes


def get_position_list():
    """
    获取所有岗位列表
    
    自动扫描简历目录，返回所有发现的岗位类型列表。
    
    Returns:
        list: 岗位类型列表
    """
    position_dirs = discover_positions()
    return list(position_dirs.keys())


def extract_candidate_info_with_llm(resume_text):
    """
    使用大模型提取候选人信息
    
    调用大模型从简历文本中提取结构化信息，包括姓名、电话、性别、年龄、学历、
    教育背景详情、工作经验、技能、项目经验、个人简介等。
    
    如果大模型调用失败或返回结果不完整，回退到传统的正则表达式提取方法。
    
    Args:
        resume_text: 简历文本内容
        
    Returns:
        dict: 包含提取结果的字典
    """
    try:
        from llm.resume_extractor import extract_resume_info_with_llm as llm_extract
        
        llm_result = llm_extract(resume_text)
        
        if llm_result:
            result = {
                'name': llm_result.get('name', ''),
                'education': llm_result.get('education', ''),
                'education_details': llm_result.get('education_details', []),
                'skills': llm_result.get('skills', ''),
                'projects': llm_result.get('projects', ''),
                'summary': llm_result.get('summary', ''),
                'phone': llm_result.get('phone', ''),
                'gender': llm_result.get('gender', ''),
                'age': llm_result.get('age', ''),
                'experience': llm_result.get('experience', ''),
                'experience_summary': llm_result.get('experience_summary', '')
            }
            return result
        
        logger.info("LLM提取失败，回退到传统方法")
        
    except Exception as e:
        logger.warning(f"调用LLM提取简历信息失败: {str(e)}，回退到传统方法")
    
    return extract_candidate_info_from_text(resume_text)


def read_resumes_for_position_with_llm(position_key, resume_dir=None):
    """
    使用大模型读取指定岗位的所有简历
    
    根据岗位关键字查找对应的简历目录，遍历目录中的所有PDF文件，
    使用大模型提取简历信息，构建候选人信息列表。
    
    Args:
        position_key: 岗位类型关键字
        resume_dir: 简历目录路径（可选，若不传则自动查找）
        
    Returns:
        list: 包含候选人信息的字典列表
    """
    candidates = []
    
    if resume_dir is None:
        position_dirs = discover_positions()
        resume_dir = position_dirs.get(position_key)
    
    if not resume_dir or not os.path.exists(resume_dir):
        logger.error(f"简历目录不存在: {resume_dir}")
        return candidates
    
    pdf_files = [f for f in os.listdir(resume_dir) if f.lower().endswith('.pdf')]
    
    logger.info(f"开始读取{position_key}岗位的简历（LLM模式），共{len(pdf_files)}份")
    
    for filename in pdf_files:
        pdf_path = os.path.join(resume_dir, filename)
        
        file_info = parse_filename(filename)
        
        text = extract_text_from_pdf(pdf_path)
        
        text_info = extract_candidate_info_with_llm(text)
        
        candidate = {
            'filename': filename,
            'name': text_info.get('name', '') or file_info['name'],
            'position': file_info['position'] or position_key,
            'experience': text_info.get('experience', '') or file_info['experience'],
            'expected_salary': file_info['expected_salary'],
            'education': text_info['education'],
            'education_details': text_info['education_details'],
            'skills': text_info['skills'],
            'projects': text_info['projects'],
            'summary': text_info['summary'],
            'phone': text_info['phone'],
            'gender': text_info['gender'],
            'age': text_info['age'],
            'full_text': text
        }
        
        candidates.append(candidate)
        logger.debug(f"已读取简历: {filename}")
    
    logger.info(f"完成{position_key}岗位简历读取（LLM模式），共{len(candidates)}份")
    
    return candidates


def get_all_resumes_with_llm():
    """
    使用大模型读取所有岗位的简历
    
    自动扫描简历目录发现所有岗位，逐个调用read_resumes_for_position_with_llm函数，
    将结果汇总到字典中返回。
    
    Returns:
        dict: 以岗位类型为键，候选人列表为值的字典
    """
    all_resumes = {}
    position_dirs = discover_positions()
    
    for position_key, resume_dir in position_dirs.items():
        all_resumes[position_key] = read_resumes_for_position_with_llm(position_key, resume_dir)
    
    return all_resumes