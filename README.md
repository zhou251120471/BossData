# 简历智能评估系统

基于大模型的自动化简历筛选与评估系统，支持多岗位简历分类处理、智能评估、优先级排序，并生成格式化的Excel评估报告。系统支持**远程大模型**和**本地大模型**两种评估模式，资源匹配（简历目录、评估标准）也会根据所选模式自动选择对应的LLM进行智能匹配，具有高度的通用性和扩展性。

## 功能特点

- 📄 **多格式简历读取**：支持PDF格式简历文本提取（优先使用PyMuPDF）
- 📋 **评估标准解析**：从Excel文件解析评估维度和优先级等级标准
- 🤖 **智能评估**：支持两种评估模式
  - 远程大模型评估（阿里云百炼API）
  - 本地大模型评估（GPU加速，自动从HuggingFace镜像下载模型）
- 🔗 **智能资源匹配**：根据评估模式自动选择远程/本地LLM匹配简历目录和评估标准文件
- 📝 **信息提取**：从简历中自动提取手机号、性别、年龄、学历等关键信息
- 📊 **优先级排序**：按P0-P3优先级等级及匹配度分数排序候选人
- 📝 **Excel输出**：生成带样式、着色的评估结果Excel文件
- 🎯 **自动发现**：自动扫描目录发现新岗位，无需修改代码
- 🔧 **通用配置**：支持任意岗位类型，提供默认评估维度配置
- 🌐 **国内镜像**：本地模型默认从 hf-mirror.com 下载，国内网络可直接使用
- 💬 **提示词集中管理**：所有LLM提示词模板统一维护在 `prompt_templates.py`，修改提示词只需改一处

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      main.py                                │
│                    主程序入口                                │
│                    - argparse参数解析                        │
│                    - 候选人批量评估                          │
│                    - 规则匹配打分（兜底）                    │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    utils/       │  │    llm/         │  │  local_llm/     │
│  resume_reader  │  │  remote_llm.py  │  │  local_model.py │
│  evaluation_    │  │  远程大模型调用  │  │  本地大模型调用  │
│   parser.py     │  │ - API调用       │  │ - 自动下载模型  │
│  data_processor │  │ - 响应解析      │  │ - HF镜像加速    │
│  excel_writer   │  └─────────────────┘  │ - GPU推理       │
│  resource_      │           │            └─────────────────┘
│   manager.py    │           │                    │
│  prompt_        │           │                    │
│   templates.py  │           │                    │
│  资源智能匹配   │           │                    │
│  提示词模板     │           │                    │
└─────────────────┘           │                    │
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │   config.py     │
                    │   配置模块       │
                    │ - 通用配置      │
                    │ - LLM配置       │
                    │ - Local LLM配置 │
                    │ - HF镜像配置    │
                    └─────────────────┘
```

## 目录结构

```
BossData2/
├── config.py                  # 系统配置文件（按模块分类）
├── main.py                    # 主程序入口（argparse参数解析 + 评估流程）
├── requirements.txt           # 项目依赖
├── .venv/                     # Python虚拟环境
├── data/                      # 数据目录
│   ├── Resumes/               # 简历存放目录（自动发现岗位）
│   │   ├── 前端开发人员的简历/    # 前端岗位简历
│   │   ├── 测试人员的简历/       # 测试岗位简历
│   │   └── 美工设计人员的简历/   # UX岗位简历
│   ├── AssessmentCriteria/    # 评估标准目录
│   │   ├── 前端组·候选人优先级等级汇总表.xlsx
│   │   ├── 测试组·候选人优先级等级汇总表.xlsx
│   │   └── UX组·候选人优先级等级汇总表.xlsx
│   ├── OutputResult/          # 输出结果目录（自动创建）
│   └── OutputResultTemplate/  # 输出模板目录
├── model/                     # 本地模型存放目录（首次运行自动下载）
│   └── Qwen2-7B-Instruct/    # 按模型名自动创建子目录
│       ├── config.json
│       ├── tokenizer.json
│       ├── model-00001-of-00004.safetensors
│       └── ...
├── llm/                       # 远程大模型模块
│   ├── __init__.py
│   └── remote_llm.py          # 远程API调用、响应解析
├── local_llm/                 # 本地大模型模块
│   ├── __init__.py
│   └── local_model.py         # 本地模型加载、自动下载、GPU推理、HF镜像
└── utils/                     # 公共工具模块
    ├── __init__.py
    ├── resume_reader.py       # 简历读取、PDF解析、自动发现岗位、手机号/性别/年龄提取
    ├── evaluation_parser.py   # 评估标准解析、自动加载
    ├── data_processor.py      # 数据处理、排序、报告生成
    ├── excel_writer.py        # Excel输出、样式设置
    ├── resource_manager.py    # 资源智能匹配（按模式选择远程/本地LLM）
    └── prompt_templates.py    # 提示词模板集中管理
```

## 环境要求

- Python 3.8+
- Windows / macOS / Linux
- 本地模型评估推荐GPU支持（NVIDIA GPU，显存≥8GB；无GPU也可用CPU运行，速度较慢）
- 网络环境：本地模型首次运行需联网下载（使用国内镜像 hf-mirror.com）

## 安装步骤

### 1. 创建虚拟环境

```bash
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置数据目录

确保数据目录结构正确：

```
data/
├── Resumes/
│   ├── 前端开发人员的简历/    # 放置前端岗位PDF简历
│   ├── 测试人员的简历/       # 放置测试岗位PDF简历
│   └── 美工设计人员的简历/   # 放置UX岗位简历
├── AssessmentCriteria/      # 放置各岗位评估标准Excel文档
├── OutputResult/            # 输出结果目录（自动创建）
└── OutputResultTemplate/    # 输出模板目录（可选）
```

### 4. 切换虚拟环境

每次打开新终端时，需要先激活虚拟环境才能运行程序：

```bash
# Windows PowerShell（注意前面的点+空格）
. .\.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat

# macOS/Linux
source .venv/bin/activate
```

**说明**：
- 激活成功后，终端提示符前会显示 `(.venv)` 标识
- 退出虚拟环境：输入 `deactivate` 即可
- 若PowerShell执行失败，可能需要修改执行策略：
  ```powershell
  # 以管理员身份运行PowerShell后执行
  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

## 使用方法

### 基本命令

```bash
# 使用远程大模型评估所有职位
python main.py --llm

# 使用本地大模型评估所有职位（GPU加速）
python main.py --local

# 使用远程大模型评估多个指定职位
python main.py --llm --positions 前端,测试

# 使用本地模型评估指定职位
python main.py --local --positions 前端

# 显示帮助信息和可用职位列表
python main.py --help
```

### 命令行参数说明
| 参数 | 说明 | 示例 |
|------|------|------|
| `--llm` | 使用远程大模型评估（需配置API） | `python main.py --llm` |
| `--local` | 使用本地大模型评估（GPU加速） | `python main.py --local` |
| `--positions 职位1,职位2` | 指定评估的职位（逗号分隔） | `python main.py --llm --positions 前端,测试` |
| `--help` / `-h` | 显示帮助信息和可用职位 | `python main.py --help` |

> **注意**：`--llm` 和 `--local` 为互斥参数，必须且只能选择其中一个。

## 评估模式

### 远程大模型评估（--llm）

调用阿里云百炼API进行深度语义分析评估。资源匹配（简历目录、评估标准文件）也会使用远程LLM进行智能匹配。

**配置方法**：编辑 `config.py` 中的 `LLM_CONFIG`：

```python
LLM_CONFIG = {
    'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'api_key': '你的API密钥',
    'model': 'qwen-max',
    'temperature': 0.1,
    'max_tokens': 2000
}
```

### 本地大模型评估（--local）

加载本地模型进行推理，支持GPU加速和4-bit量化。资源匹配使用本地LLM进行智能匹配。

**首次运行**：如果本地 `model` 目录下没有模型文件，系统会自动从 HuggingFace 国内镜像（hf-mirror.com）下载模型，下载后保存到 `model/模型名/` 子目录，下次直接从本地加载，无需重复下载。

**配置方法**：编辑 `config.py` 中的 `LOCAL_LLM_CONFIG`：

```python
LOCAL_LLM_CONFIG = {
    'model_path': os.path.join(BASE_DATA_PATH, 'model'),  # 模型存放根目录
    'model_name': 'qwen2-7b-instruct',                    # 模型名称（支持简写和完整ID）
    'hf_mirror': 'https://hf-mirror.com',                 # HuggingFace国内镜像
    'device_map': 'auto',
    'max_tokens': 2000,
    'temperature': 0.1,
    'load_in_4bit': True
}
```

**模型名称映射**：`model_name` 支持简写，系统会自动转换为完整的 HuggingFace ID：

| 简写 | 完整ID |
|------|--------|
| `qwen2-7b-instruct` | `Qwen/Qwen2-7B-Instruct` |
| `qwen2-1.5b-instruct` | `Qwen/Qwen2-1.5B-Instruct` |
| `qwen2.5-7b-instruct` | `Qwen/Qwen2.5-7B-Instruct` |
| `qwen2.5-3b-instruct` | `Qwen/Qwen2.5-3B-Instruct` |
| `Qwen/Qwen2.5-7B-Instruct` | 直接使用（含 `/` 的完整ID） |

**模型目录结构**：不同模型自动存放在不同子目录，互不干扰：

```
model/
├── Qwen2-7B-Instruct/          # qwen2-7b-instruct 的模型文件
│   ├── config.json
│   ├── tokenizer.json
│   ├── model-00001-of-00004.safetensors
│   └── ...
└── Qwen2.5-3B-Instruct/        # 换模型后自动创建新子目录
    └── ...
```

**注意**：
- 首次运行需联网下载模型（约15GB for 7B模型，4bit量化后约4GB）
- 推荐NVIDIA RTX 3060以上显卡（显存≥8GB）
- 无GPU也可用CPU运行，但推理速度较慢

### 规则匹配评估（兜底）

当LLM评估失败或响应解析失败时，系统自动回退到基于关键词匹配的规则评估。系统会自动匹配简历内容与评估标准中的关键词，根据匹配程度计算得分。

评估维度（可配置）：
- 核心技能匹配度（权重30%）
- 经验年限与学历（权重25%）
- 项目经验与产出（权重25%）
- 综合能力（权重20%）

## 提示词模板管理

所有LLM提示词模板集中管理在 `utils/prompt_templates.py`，修改提示词只需改这一个文件。

### 模板列表

| 模板 | 类型 | 用途 | 使用位置 |
|------|------|------|----------|
| `RESOURCE_MATCH_SYSTEM_PROMPT` | 常量 | 资源匹配的system_prompt | resource_manager.py |
| `EVALUATION_SYSTEM_PROMPT` | 常量 | 简历评估的system_prompt | remote_llm.py, local_model.py, config.py |
| `build_resource_match_prompt()` | 函数 | 构建资源匹配提示词（岗位名→资源名） | resource_manager.py |
| `build_candidate_info_text()` | 函数 | 构建候选人信息展示文本 | remote_llm.py |
| `EVALUATION_INSTRUCTION` | 常量 | 评估指令+JSON输出格式定义 | remote_llm.py |

### 评估提示词结构

发给大模型的完整评估提示词由四部分拼接：

```
评估标准文本 (criteria_text)
+ 动态权重计算规则 (dynamic_weight_text)
+ 候选人信息 (build_candidate_info_text)
+ 评估指令 (EVALUATION_INSTRUCTION)
```

### 资源匹配流程

用户输入的岗位名（如"前端"）通过LLM语义理解，分别独立匹配简历目录和评估标准文件：

```
"前端" ──LLM──→ "前端开发人员的简历"      (简历目录匹配)
"前端" ──LLM──→ "前端组·岗位评估标准.xlsx" (评估标准匹配)
```

## 优先级等级定义

| 等级 | 名称 | 分数范围 | 推荐行动 |
|------|------|----------|----------|
| P0 | 优先推荐 | 85-100 | 直接安排面试，重点跟进 |
| P1 | 推荐 | 70-84 | 安排面试，重点验证短板 |
| P2 | 备选 | 50-69 | 进入备选池，视进度再议 |
| P3 | 暂不推荐 | 0-49 | 婉拒或转推荐 |

## 配置说明

### 配置文件结构

`config.py` 按模块分类配置：

```python
# 通用配置
COMMON_CONFIG = {
    'data_path': '数据目录路径',
    'resumes_path': '简历目录路径',
    'priority_levels': {...},
    'default_evaluation_dimensions': [...]  # 通用评估维度
}

# 远程大模型配置
LLM_CONFIG = {
    'api_base': 'API地址',
    'api_key': 'API密钥',
    'model': '模型名称',
    ...
}

# 本地大模型配置
LOCAL_LLM_CONFIG = {
    'model_path': '模型存放根目录',
    'model_name': '模型名称（支持简写）',
    'hf_mirror': 'https://hf-mirror.com',  # HuggingFace国内镜像
    'device_map': 'auto',
    'load_in_4bit': True
}
```

### 添加新岗位

系统支持**自动发现**新岗位，只需：

1. 在 `data/Resumes/` 目录下创建新的岗位文件夹（如 `后端开发人员的简历/`）
2. 在 `data/AssessmentCriteria/` 目录下创建对应的评估标准Excel文件（如 `后端组·候选人优先级等级汇总表.xlsx`）

系统会自动扫描并识别新岗位，无需修改代码。

### 修改评估维度

编辑 `config.py` 中的 `EVALUATION_DIMENSIONS`：

```python
EVALUATION_DIMENSIONS = {
    '前端': [
        {'id': 'D1', 'name': '核心技术栈匹配度', 'weight': 30, 'standard': '精通Vue3+TypeScript...'},
        {'id': 'D2', 'name': '经验年限与学历', 'weight': 20, 'standard': '本科及以上...'},
        # ...
    ],
    # 添加其他岗位配置...
}
```

对于没有特定配置的岗位，系统会使用 `default_evaluation_dimensions` 通用配置。

## 输出文件

系统为每个岗位生成独立的Excel评估结果文件：

- **岗位名称候选人评估结果.xlsx** - 各岗位详细评估结果

### Excel内容说明

| 字段 | 说明 |
|------|------|
| 序号 | 排名（按优先级和匹配度） |
| 姓名 | 候选人姓名 |
| 手机号 | 联系电话 |
| 性别 | 性别 |
| 年龄 | 年龄 |
| 学历 | 学历信息 |
| 工作经验（年限） | 从业年限 |
| 核心技能/工具 | 掌握的技能 |
| 核心亮点 | 候选人主要优势 |
| 主要差距 | 候选人主要不足 |
| 意向（擅长）模块 | 擅长的领域/模块（如ERP、CRM、项目管理软件等） |
| 应聘岗位 | 应聘的岗位 |
| 前期信息了解 | 提取的基本信息 |
| 综合匹配度 | 综合评分（0-100%） |
| 优先级 | P0-P3等级（带颜色标记） |
| 定级理由 | 评分理由 |
| 处理动作 | 推荐行动 |

### Excel排版样式

系统生成的Excel文件包含专业的排版样式，提升可读性：

#### 表头样式
- **背景色**：深蓝色（RGB: 44, 114, 196）
- **字体**：微软雅黑、加粗、白色、12号字
- **对齐**：居中对齐、垂直居中、自动换行
- **行高**：28像素

#### 数据行样式
- **奇偶行条纹效果**：奇数行白色背景、偶数行浅灰色背景（#F2F2F2）
- **对齐方式**：文本左对齐、数字/匹配度/优先级居中对齐
- **行高**：根据内容长度自动调整（20-35像素）

#### 优先级着色
| 优先级 | 背景色 | 字体颜色 |
|--------|--------|----------|
| P0 | 深绿色 | 白色加粗 |
| P1 | 深黄色 | 白色加粗 |
| P2 | 深橙色 | 白色加粗 |
| P3 | 绿色 | 白色加粗 |

#### 匹配度着色
| 匹配度 | 背景色 | 字体颜色 |
|--------|--------|----------|
| ≥80% | 浅绿色 | 深绿色加粗 |
| 60-80% | 浅黄色 | 深黄色加粗 |
| <60% | 浅红色 | 深红色加粗 |

#### 列宽优化
- 根据中文/英文比例自动计算宽度（中文×1.5，英文×0.9）
- 特殊列设置固定宽度：
  - 手机号：15
  - 核心技能/工具：35
  - 核心亮点：45
  - 主要差距：40
  - 教育背景详情：40

#### 边框
- 所有单元格添加细边框，表格结构清晰

## 依赖列表

| 依赖 | 用途 |
|------|------|
| PyMuPDF (fitz) | PDF文本提取（优先） |
| PyPDF2 | PDF文本提取（备选） |
| openpyxl | Excel文件读写 |
| requests | HTTP请求（远程API） |
| transformers | 本地模型加载与推理 |
| torch | PyTorch深度学习框架 |
| accelerate | GPU加速与分布式训练 |
| bitsandbytes | 4-bit量化 |
| logging | 日志记录（标准库） |

## 常见问题

### Q1: 运行时报"Odd-length string"错误

**原因**：某些PDF文件编码格式异常

**处理**：系统会自动捕获异常并跳过该文件，继续处理其他简历

### Q2: 大模型评估不生效

**检查**：确认 `config.py` 中 `LLM_CONFIG` 的 `api_base` 和 `api_key` 是否配置正确

### Q3: 本地模型加载失败

**检查**：
1. 首次运行会自动从 HuggingFace 镜像下载模型，请确认网络可访问 `https://hf-mirror.com`
2. 确认 `config.py` 中 `hf_mirror` 配置正确
3. 确认已安装GPU驱动和CUDA（GPU模式）
4. 确认显存足够（推荐≥8GB）
5. 如果模型下载中断，删除 `model/模型名/` 目录后重新运行即可重新下载

### Q4: 如何更换本地模型

修改 `config.py` 中的 `model_name` 即可，系统会自动在新子目录下载新模型：

```python
# 换成更小的3B模型（显存要求更低）
'model_name': 'qwen2.5-3b-instruct'

# 或直接使用完整HuggingFace ID
'model_name': 'Qwen/Qwen2.5-3B-Instruct'
```

### Q5: 评估结果Excel文件未生成

**检查**：确认 `data/OutputResult` 目录是否存在且有写入权限

### Q6: 新岗位没有评估标准

**处理**：系统会自动使用 `default_evaluation_dimensions` 通用配置进行评估，也可以添加对应的Excel评估标准文件

### Q7: 如何修改提示词

所有提示词模板集中在 `utils/prompt_templates.py` 文件中，修改该文件即可全局生效：

- `RESOURCE_MATCH_SYSTEM_PROMPT` / `build_resource_match_prompt()` — 资源匹配相关
- `EVALUATION_SYSTEM_PROMPT` — 评估的system_prompt
- `build_candidate_info_text()` — 候选人信息展示格式
- `EVALUATION_INSTRUCTION` — 评估指令和JSON输出格式

### Q8: 循环导入报错 (ImportError)

**原因**：`config.py` 不能导入 `utils` 包下的模块，否则会触发循环导入

**处理**：`config.py` 保持为纯配置文件，不导入任何 `utils` 模块。提示词常量由各使用方直接从 `prompt_templates.py` 导入

## License

MIT License

## 作者

简历智能评估系统开发团队