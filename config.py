"""
简历智能评估系统 - 配置文件

该模块定义系统的所有配置项，按功能模块分类：

1. 通用配置（COMMON_CONFIG）
   - 数据路径配置
   - 岗位与简历目录映射
   - 优先级等级定义
   - 输出配置

2. LLM配置（LLM_CONFIG）
   - 远程大模型API配置
   - 提示词模板配置

3. Local_LLM配置（LOCAL_LLM_CONFIG）
   - 本地大模型路径和参数

4. 模型关键词配置（SKILL_KEYWORDS / MODULE_KEYWORDS）
   - 技能关键词映射
   - 模块关键词映射

使用说明：
1. 修改COMMON_CONFIG中的BASE_DATA_PATH为项目根目录
2. 使用大模型评估前，请配置LLM_CONFIG中的api_base和api_key
3. 使用本地模型前，请配置LOCAL_LLM_CONFIG中的model_path
"""

import os

# ==================== 通用配置 ====================
COMMON_CONFIG = {
    'base_data_path': os.path.dirname(os.path.abspath(__file__)),
    'data_path': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'),
    'resumes_path': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'Resumes'),
    'assessment_criteria_path': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'AssessmentCriteria'),
    'output_path': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'OutputResult'),
    'output_template_path': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'OutputResultTemplate', '简历推荐信息汇总.xlsx'),
    
    'output_columns': [
        '序号', '姓名', '手机号', '性别', '年龄', '最高学历', '教育背景详情',
        '工作经验（年限）', '核心技能/工具', '核心亮点', '主要差距', '意向（擅长）模块',
        '应聘岗位', '期望月薪', '前期信息了解', '综合匹配度', '优先级', '处理动作'
    ],
    
    'priority_levels': {
        'P0': {'name': '优先推荐', 'min_score': 85, 'max_score': 100, 'action': '直接安排面试，重点跟进'},
        'P1': {'name': '推荐', 'min_score': 70, 'max_score': 84, 'action': '安排面试，重点验证短板'},
        'P2': {'name': '备选', 'min_score': 50, 'max_score': 69, 'action': '进入备选池，视进度再议'},
        'P3': {'name': '暂不推荐', 'min_score': 0, 'max_score': 49, 'action': '婉拒或转推荐'}
    },
    
    'priority_order': ['P0', 'P1', 'P2', 'P3']
}

# ==================== LLM配置（远程大模型） ====================
# Plus类模型 :多模态模型
# max类模型：推理能力强，但不支持多模态
LLM_CONFIG = {
    'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'api_key': 'sk-e0453f8ef23b4d80b7f89445fd251afc',
    # 'model': 'qwen-max',
    # 'model': 'qwen3.7-max',
    # 'model': 'qwen3.7-plus',
    'model': 'qwen3.7-plus',
    'temperature': 0.1,
    'max_tokens': 4000,
    'max_retries': 4,
    'timeout_connect': 120,
    'timeout_read': 300,
    'system_prompt': '你是一个专业的技术招聘评估专家，擅长根据岗位要求对候选人进行客观、准确的评估。',
    
    'prompt_template': {
        'evaluation_format':
            """请按照以下JSON格式输出评估结果：
            {
                "match_score": 85,
                "priority": "P0",
                "core_strengths": "候选人的核心优势描述",
                "main_risks": "候选人的主要风险描述",
                "suggested_action": "建议动作",
                "rating_reason": "定级理由",
                "intention_modules": "ERP,财务系统,数据可视化",
                "preliminary_info": "5年前端开发经验，精通Vue3+TypeScript，有组件库开发经验",
                "dimension_scores": {
                    "D1": 90,
                    "D2": 80,
                    "D3": 85,
                    "D4": 85
                },
                "dimension_details": {
                    "D1": {
                        "matched_items": 4,
                        "total_items": 5,
                        "score": 24,
                        "comments": "符合4项达标标准"
                    }
                }
            }"""
    }
}


# ==================== Local_LLM配置（本地大模型） ====================
# qwen2-7b-instruct: 多模态模型
# model_path：文件存储地址
# hf_mirror：模型镜像地址
# model_name：模型名称
# device_map：设备映射，auto表示自动选择，cpu表示CPU，cuda表示GPU
# max_tokens：最大输出token数
# temperature：温度参数，控制输出的随机性
# top_p：top-p采样参数，控制输出的随机性
# load_in_4bit：是否加载4位模型，减少内存占用和计算时间
# trust_remote_code：是否信任远程代码，用于加载本地模型
# max_input_length：最大输入长度
LOCAL_LLM_CONFIG = {
    'model_path': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model'),
    'model_name': 'qwen2-7b-instruct',
    'hf_mirror': 'https://hf-mirror.com',
    'device_map': 'auto',
    'max_tokens': 2000,
    'temperature': 0.1,
    'top_p': 0.9,
    'load_in_4bit': True,
    'trust_remote_code': True,
    'max_input_length': 4096,
    'system_prompt': '你是一个专业的技术招聘评估专家，擅长根据岗位要求对候选人进行客观、准确的评估。'
}

# ==================== 模型关键词配置 ====================没用到
SKILL_KEYWORDS = {
    '前端框架': {
        'React': ['react', 'react.js', 'reactjs', 'react native', 'next.js', 'remix'],
        'Vue': ['vue', 'vue.js', 'vuejs', 'vue2', 'vue3', 'nuxt.js', 'pinia', 'vuex'],
        'Angular': ['angular', 'angularjs', 'angular2', 'ng'],
        'Svelte': ['svelte', 'sveltekit'],
        'Solid': ['solid', 'solidjs']
    },
    '编程语言': {
        'JavaScript': ['javascript', 'js', 'es6', 'es7', 'es8', 'ecmascript'],
        'TypeScript': ['typescript', 'ts'],
        'Python': ['python', 'py'],
        'Java': ['java', 'jdk', 'spring', 'springboot'],
        'Go': ['golang', 'go语言'],
        'C++': ['c++', 'cpp'],
        'C#': ['c#', 'csharp']
    },
    '构建工具': {
        'Webpack': ['webpack', 'webpack5'],
        'Vite': ['vite'],
        'Rollup': ['rollup'],
        'Gulp': ['gulp'],
        'Grunt': ['grunt']
    },
    '数据库': {
        'MySQL': ['mysql'],
        'PostgreSQL': ['postgresql', 'postgres'],
        'MongoDB': ['mongodb', 'mongo'],
        'Redis': ['redis'],
        'Oracle': ['oracle'],
        'SQL Server': ['sql server', 'mssql']
    },
    '技术模块': {
        'ERP': ['erp', '企业资源计划', '供应链管理', '进销存', '财务系统'],
        'CRM': ['crm', '客户关系管理', '销售管理', '客户管理'],
        'OA': ['oa', '办公自动化', '协同办公', '钉钉', '企业微信'],
        '电商': ['电商', '电子商务', '在线购物', '商城', '淘宝', '京东'],
        '大数据': ['大数据', '数据仓库', 'etl', 'hadoop', 'spark', 'flink'],
        '人工智能': ['人工智能', 'ai', '机器学习', '深度学习', 'tensorflow', 'pytorch'],
        '微服务': ['微服务', 'microservice', 'docker', 'kubernetes', 'k8s'],
        '微前端': ['微前端', 'qiankun', 'micro-frontend']
    },
    '测试工具': {
        '自动化测试': ['selenium', 'playwright', 'cypress', 'testcafe'],
        '接口测试': ['postman', 'jmeter', 'api测试', '接口自动化'],
        '性能测试': ['性能测试', 'loadrunner', 'locust'],
        '单元测试': ['jest', 'mocha', 'pytest', 'unittest']
    },
    '设计工具': {
        'Figma': ['figma'],
        'Sketch': ['sketch'],
        'MasterGo': ['mastergo', 'mg'],
        'Photoshop': ['photoshop', 'ps'],
        'Illustrator': ['illustrator', 'ai'],
        'Axure': ['axure']
    }
}

MODULE_KEYWORDS = {
    'erp': ['erp', '企业资源计划'],
    '财务': ['财务', 'finance', 'accounting'],
    '供应链': ['供应链', 'supply chain', 'scm'],
    '数据可视化': ['数据可视化', '大屏', 'dashboard', 'visualization'],
    '组件库': ['组件库', 'component', 'design system'],
    '微前端': ['微前端', 'micro frontend', 'qiankun'],
    '自动化测试': ['自动化', 'automation', 'selenium', 'appium'],
    '性能测试': ['性能测试', 'jmeter', 'locust', '性能优化'],
    'B端设计': ['B端', '企业级', 'tob'],
    '移动端': ['移动端', 'mobile', 'ios', 'android'],
    '后端开发': ['后端', 'backend', 'java', 'nodejs'],
    '低代码': ['低代码', 'low code', 'amis'],
    '金融': ['金融', '银行', 'finance'],
    '医疗': ['医疗', 'healthcare', 'hospital'],
    '电商': ['电商', 'e-commerce', 'shopping'],
    '教育': ['教育', 'education', 'learning']
}

# ==================== 日志配置 ====================
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': 'INFO'
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO'
    }
}

# ==================== 快捷访问变量（保持向后兼容） ====================
BASE_DATA_PATH = COMMON_CONFIG['base_data_path']
DATA_PATH = COMMON_CONFIG['data_path']
RESUMES_PATH = COMMON_CONFIG['resumes_path']
ASSESSMENT_CRITERIA_PATH = COMMON_CONFIG['assessment_criteria_path']
OUTPUT_PATH = COMMON_CONFIG['output_path']
OUTPUT_TEMPLATE_PATH = COMMON_CONFIG['output_template_path']
OUTPUT_COLUMNS = COMMON_CONFIG['output_columns']
PRIORITY_LEVELS = COMMON_CONFIG['priority_levels']
PRIORITY_ORDER = COMMON_CONFIG['priority_order']
