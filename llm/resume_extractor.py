"""
简历智能评估系统 - 大模型简历信息提取模块

该模块负责使用大模型从简历文本中提取结构化信息，包括：
1. 基本信息：姓名、电话、性别、年龄
2. 教育背景：最高学历、教育背景详情（年份、学校、专业、学历）
3. 工作经验：年限、经验摘要
4. 技能：核心技能列表
5. 项目经验：项目经历摘要
6. 个人简介：自我评价

核心特点：
- 使用大模型理解非结构化文本，提取准确率远高于正则表达式
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

RESUME_EXTRACTION_SYSTEM_PROMPT = """你是一个专业的简历信息提取专家，擅长从非结构化简历文本中提取结构化信息。请仔细阅读简历内容，准确提取以下字段。"""


def build_resume_extraction_prompt(resume_text):
    """
    构建简历信息提取Prompt
    
    将简历文本和提取要求组合成大模型可理解的Prompt，要求大模型输出JSON格式的结构化信息。
    
    Args:
        resume_text: 简历文本内容
        
    Returns:
        str: 构建好的Prompt文本
    """
    prompt = f"""请仔细阅读以下简历文本，提取所有关键信息，并按照指定的JSON格式输出。

【简历文本】
{resume_text}

【提取要求】
请从上述简历中提取以下信息：

1. 基本信息：
   - name: 姓名（如果有多个姓名，提取主姓名）
   - phone: 手机号码（11位数字）
   - gender: 性别（男/女）
   - age: 年龄（数字，如28；如果只有出生年份，计算年龄）

2. 教育背景：
   - education: 最高学历（博士/硕士/本科/大专/专科/高中/中专）
   - education_details: 教育背景详情数组，每个元素包含：
     * start_year: 入学年份（4位数字）
     * end_year: 毕业年份（4位数字，未毕业填""）
     * school: 学校名称（完整名称，如"安徽农业大学经济技术学院"）
     * major: 专业名称（如"计算机科学与技术"）
     * degree: 学历（本科/硕士/大专等）

3. 工作经验：
   - experience: 工作年限（如"5年"、"10年以上"）
   - experience_summary: 工作经验摘要（从工作经历中提取关键信息）

4. 技能：
   - skills: 核心技能列表，用分号分隔（如"Vue3; TypeScript; Webpack"）

5. 项目经验：
   - projects: 项目经验摘要（提取3-5个主要项目的关键信息）

6. 个人简介：
   - summary: 个人简介/自我评价（提取主要内容，不超过300字）

【输出格式要求】
请严格按照以下JSON格式输出，不要输出其他任何内容：
{{
    "name": "姓名",
    "phone": "13800138000",
    "gender": "男",
    "age": "28",
    "education": "本科",
    "education_details": [
        {{
            "start_year": "2013",
            "end_year": "2017",
            "school": "河南科技学院",
            "major": "计算机科学与技术",
            "degree": "本科"
        }}
    ],
    "experience": "9年",
    "experience_summary": "工作经验摘要内容",
    "skills": "Vue3; TypeScript; Webpack",
    "projects": "项目经验摘要内容",
    "summary": "个人简介内容"
}}

【重要注意事项】
- 如果某个字段在简历中未找到，请填空字符串""
- education_details数组中每个元素必须包含start_year、end_year、school、major、degree字段
- 学校名称必须完整提取，不要截断（如"安徽农业大学经济技术学院"不要截断为"安徽农业大学"）
- 技能列表要尽量完整，包含所有提到的技术栈
- 工作年限要从工作经历或简历其他部分提取
- 只输出JSON，不要输出其他任何解释或说明文字
"""

    return prompt


def parse_resume_extraction_response(response_text):
    """
    解析大模型返回的简历提取结果
    
    从大模型响应中提取JSON格式的简历信息，进行必要的数据清洗和校验。
    
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
                'name': data.get('name', '').strip(),
                'phone': data.get('phone', '').strip(),
                'gender': data.get('gender', '').strip(),
                'age': data.get('age', '').strip(),
                'education': data.get('education', '').strip(),
                'education_details': data.get('education_details', []),
                'experience': data.get('experience', '').strip(),
                'experience_summary': data.get('experience_summary', '').strip(),
                'skills': data.get('skills', '').strip(),
                'projects': data.get('projects', '').strip(),
                'summary': data.get('summary', '').strip()
            }
            
            if result['education_details'] and isinstance(result['education_details'], list):
                for edu in result['education_details']:
                    if isinstance(edu, dict):
                        edu['start_year'] = edu.get('start_year', '').strip()
                        edu['end_year'] = edu.get('end_year', '').strip()
                        edu['school'] = edu.get('school', '').strip()
                        edu['major'] = edu.get('major', '').strip()
                        edu['degree'] = edu.get('degree', '').strip()
            
            if result['name']:
                return result
            
            logger.warning(f"JSON解析成功但name为空，响应前200字: {cleaned_text[:200]}")
            return None
        
        logger.warning(f"未找到JSON格式数据，响应前300字: {cleaned_text[:300]}")
        return None
        
    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失败: {e}")
        return None
    except Exception as e:
        logger.error(f"解析简历提取响应失败: {str(e)}")
        return None


def extract_resume_info_with_llm(resume_text, config=None):
    """
    使用大模型提取简历信息
    
    调用大模型API，从简历文本中提取结构化信息。
    如果大模型调用失败，返回None（由调用方决定是否使用回退方法）。
    
    Args:
        resume_text: 简历文本内容
        config: API配置（可选，默认使用LLM_CONFIG）
        
    Returns:
        dict: 包含提取结果的字典，若调用失败返回None
    """
    if not resume_text or len(resume_text.strip()) < 10:
        logger.warning("简历文本为空或过短，无法提取信息")
        return None
    
    if config is None:
        config = LLM_CONFIG
    
    api_base = config.get('api_base', '')
    api_key = config.get('api_key', '')
    
    if not api_base or not api_key:
        logger.warning("大模型API配置不完整，跳过LLM提取")
        return None
    
    try:
        prompt = build_resume_extraction_prompt(resume_text)
        
        extraction_config = config.copy()
        extraction_config['system_prompt'] = RESUME_EXTRACTION_SYSTEM_PROMPT
        extraction_config['max_tokens'] = 3000
        
        response = call_llm_api(prompt, config=extraction_config)
        
        if response:
            result = parse_resume_extraction_response(response)
            if result:
                logger.info(f"LLM简历提取成功，姓名: {result.get('name', '未知')}")
                return result
            logger.warning("LLM简历提取响应解析失败")
        
        return None
        
    except Exception as e:
        logger.error(f"使用大模型提取简历信息失败: {str(e)}")
        return None