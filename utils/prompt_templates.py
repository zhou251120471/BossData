"""
简历智能评估系统 - 提示词模板模块

集中管理所有LLM提示词模板，包括：
1. 资源匹配提示词：将用户输入的岗位名与系统资源做语义匹配
2. 候选人信息模板：结构化展示候选人信息
3. 评估指令提示词：指导大模型如何评估候选人及输出格式
"""

RESOURCE_MATCH_SYSTEM_PROMPT = '你是一个智能匹配助手，只返回匹配的资源名称，不要其他解释。'

EVALUATION_SYSTEM_PROMPT = '你是一个专业的技术招聘评估专家，擅长根据岗位要求对候选人进行客观、准确的评估。'


def build_resource_match_prompt(user_input, resource_type, resources):
    """
    构建资源匹配提示词

    将用户输入的岗位名与系统资源列表一起发给LLM，
    让LLM根据语义相似度返回最匹配的资源名称。

    Args:
        user_input: 用户输入的岗位名称（如"前端"）
        resource_type: 资源类型（简历目录/评估标准/规则文件）
        resources: 可用资源字典

    Returns:
        str: 提示词
    """
    resource_list = list(resources.keys())

    prompt = f"""你是一个智能匹配助手，需要将用户的输入与系统中的资源进行匹配。
        
        用户输入: {user_input}
        
        系统中的{resource_type}资源列表:
        {chr(10).join([f'{i+1}. {r}' for i, r in enumerate(resource_list)])}
        
        请根据语义相似度，返回最匹配的资源名称。
        只返回资源名称，不要其他解释。
        如果不确定，返回空字符串。"""

    return prompt


def build_candidate_info_text(candidate):
    """
    构建候选人信息展示文本

    将候选人结构化信息拼成格式化文本，作为评估提示词的一部分。

    Args:
        candidate: 候选人信息字典

    Returns:
        str: 格式化的候选人信息文本
    """
    candidate_info = f"""【候选人信息】
        
        姓名：{candidate.get('name', '')}
        性别：{candidate.get('gender', '')}
        年龄：{candidate.get('age', '')}
        手机号：{candidate.get('phone', '')}
        应聘岗位：{candidate.get('position', '')}
        工作经验：{candidate.get('experience', '')}
        学历：{candidate.get('education', '')}
        核心技能：{candidate.get('skills', '')}
        项目经验摘要：{candidate.get('projects', '')[:500]}
        个人简介：{candidate.get('summary', '')[:500]}
        完整简历文本：{candidate.get('full_text', '')[:1000]}
        """

    return candidate_info


EVALUATION_INSTRUCTION = """请根据上述评估标准和动态权重计算规则，对候选人进行全面评估。
        
        评估要求：
        1. 按照评估维度逐项分析，每个维度的达标标准包含多个子项
        2. 对每个维度进行0-5分评分（每符合1项+1分，最多5分），直接给出最终分数
        3. 计算每个维度的加权分数：weighted_score = (维度分数 / 5) * dimension_weight
        4. 综合计算匹配度分数（0-100分），即所有维度加权分数之和，根据匹配度确定优先级等级（P0/P1/P2/P3）
        5. 从项目经验和自我评价中总结候选人的意向（擅长）模块，用逗号分隔多个值。意向模块是指候选人擅长或有意向从事的业务领域/产品方向，常见类别包括但不限于：ERP（企业资源计划）、OA（办公自动化）、CRM（客户关系管理）、项目管理软件、HRM（人力资源管理）、SCM（供应链管理）、财务管理软件、BI（数据分析与商业智能）、企业协作与通讯软件、研发与产品生命周期管理（PLM）、供应链与制造执行系统（MES/WMS/TMS）、企业知识管理与文档系统（KMS/DMS）、客户服务与支持系统（SaaS客服）、电子合同与法务合规系统、IT服务与资产管理（ITSM/EAM）、流程自动化与低代码平台（BPM/iPaaS）。请根据候选人实际项目经验归纳，不要局限于上述类别
        6. 从项目经验、个人评价、专业技能三方面提取前期信息了解内容
        7. 分析候选人的核心优势和主要风险
        8. 给出定级理由和建议动作
        
        请按照以下JSON格式输出评估结果（注意：以下仅为格式示例，match_score和priority必须根据候选人实际情况计算，不要照搬示例数值）：
        {
            "match_score": 72,
            "priority": "P1",
            "phone": "13800138000",
            "gender": "男",
            "age": "28",
            "education": "本科",
            "core_strengths": "候选人的核心优势描述",
            "main_risks": "候选人的主要风险描述",
            "suggested_action": "建议动作",
            "rating_reason": "定级理由",
            "intention_modules": "ERP,财务系统,数据可视化",
            "preliminary_info": "5年前端开发经验，精通Vue3+TypeScript，有组件库开发经验",
            "dimension_scores": {
                "D1": 3,
                "D2": 5,
                "D3": 4,
                "D4": 3
            },
            "dimension_details": {
                "D1": {
                    "score": 3,
                    "weighted_score": 18,
                    "comments": "符合3项达标标准"
                },
                "D2": {
                    "score": 5,
                    "weighted_score": 20,
                    "comments": "全部符合"
                },
                "D3": {
                    "score": 4,
                    "weighted_score": 20,
                    "comments": "符合4项达标标准"
                },
                "D4": {
                    "score": 3,
                    "weighted_score": 15,
                    "comments": "符合3项达标标准"
                }
            }
        }
        
        注意：
        - match_score必须是0-100的整数，等于所有维度weighted_score之和，严禁直接使用示例中的数值
        - priority必须是P0/P1/P2/P3之一，根据match_score确定：85分以上P0，70-84分P1，50-69分P2，50分以下P3
        - phone、gender、age、education请从简历文本中提取，若简历中未提及则填空字符串
        - intention_modules是从项目经验、自我评价中总结的擅长模块，多个用逗号分隔，如"ERP,CRM,项目管理软件"等
        - preliminary_info是从项目经验、个人评价、专业技能中提取的综合信息
        - core_strengths和main_risks请用简明扼要的语言描述
        - rating_reason是定级理由，说明为何给出该优先级
        - dimension_scores中的D1-D4对应各评估维度的0-5分评分
        - dimension_details必须包含每个维度的score（0-5分）、weighted_score和comments字段
        - weighted_score = (score / 5) * dimension_weight，结果保留整数
        - 只输出JSON，不要输出其他内容
        """

LOCAL_EVALUATION_INSTRUCTION = """请根据上述评估标准对候选人进行评估，严格按以下JSON格式输出结果。

重要：match_score必须是你根据候选人实际情况计算的真实分数，不要照抄示例数值！

输出格式：
{"match_score":72,"priority":"P1","phone":"","gender":"","age":"","education":"","core_strengths":"优势描述","main_risks":"风险描述","suggested_action":"建议动作","rating_reason":"定级理由","intention_modules":"ERP,CRM","preliminary_info":"综合信息","dimension_scores":{"D1":70,"D2":75,"D3":68,"D4":72},"dimension_details":{"D1":{"matched_items":3,"total_items":5,"score":18,"comments":"说明"}}}

评分规则：
- match_score：0-100整数，根据达标项实际匹配情况计算
- priority：85分以上P0，70-84分P1，50-69分P2，50分以下P3
- 只输出JSON，不要输出其他任何内容
"""