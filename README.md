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
BossData/
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
    ├── prompt_templates.py    # 提示词模板集中管理
    └── evaluation_validator.py# 评估结果验证
```

## 环境要求

| 项目 | 要求 |
|------|------|
| Python版本 | **3.10 或 3.11**（推荐），最低支持 3.8+ |
| 操作系统 | Windows 10/11（推荐）、macOS、Linux |
| GPU支持 | 本地模型评估推荐NVIDIA GPU，显存≥8GB；无GPU可用CPU运行（速度较慢） |
| 网络环境 | 本地模型首次运行需联网下载（使用国内镜像 hf-mirror.com） |

> **Python版本选择建议**：
> - **推荐 Python 3.10**：兼容性最好，与PyTorch 2.x、transformers等库配合最稳定
> - **Python 3.11**：性能更好，但部分旧版依赖可能不兼容
> - **Python 3.8/3.9**：可用，但PyTorch新版本支持有限
> - **不推荐 Python 3.12+**：部分依赖（如bitsandbytes）可能存在兼容性问题

## 安装步骤

### 1. 安装Python（首次使用时）

> **时机**：系统未安装Python或版本低于3.8时。

**Windows系统：**

1. 访问 [Python官网](https://www.python.org/downloads/windows/) 下载 Python 3.10 或 3.11 安装包
2. 运行安装程序，**务必勾选 "Add Python to PATH"**
3. 点击 "Install Now" 完成安装
4. 验证安装：
   ```bash
   python --version  # 应显示 Python 3.10.x 或 3.11.x
   ```

**macOS系统：**

```bash
# 使用Homebrew安装
brew install python@3.10

# 验证安装
python3 --version
```

**Linux系统（Ubuntu/Debian）：**

```bash
# 安装Python 3.10
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-dev

# 验证安装
python3.10 --version
```

### 2. 切换到项目目录（每次打开终端操作项目时）

```bash
# Windows PowerShell/CMD
cd D:\Project\BossData

# macOS/Linux
cd /path/to/BossData
```

### 3. 创建虚拟环境（首次使用或项目迁移时）

> **时机**：首次克隆项目或迁移到新环境时。

```bash
# Windows PowerShell（使用系统Python创建）
python -m venv .venv

# macOS/Linux（使用系统Python创建）
python3 -m venv .venv
```

### 4. 激活虚拟环境（每次打开新终端运行程序时）

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

### 5. 配置数据目录（首次使用时）

> **时机**：首次使用项目时，确保数据目录结构正确。

```
data/
├── Resumes/
│   ├── 前端开发人员的简历/    # 放置前端岗位PDF简历
│   ├── 测试人员的简历/       # 放置测试岗位简历
│   └── 美工设计人员的简历/   # 放置UX岗位简历
├── AssessmentCriteria/      # 放置各岗位评估标准Excel文档
├── OutputResult/            # 输出结果目录（自动创建）
└── OutputResultTemplate/    # 输出模板目录（可选）
```

### 6. 安装基础依赖（每次更换环境或requirements.txt更新时）

> **时机**：激活虚拟环境后，首次安装或requirements.txt更新时。

```bash
pip install -r requirements.txt
```

### 7. 安装GPU版本PyTorch（需要GPU加速时）

> **时机**：只有使用 `--local` 模式且需要GPU加速时才需要安装。

当前 `requirements.txt` 中的 `torch>=2.0.0` 默认安装 **CPU版本**。若要启用GPU加速，需单独安装 **CUDA版本** 的PyTorch：

**Windows系统（推荐CUDA 11.8）：**

```bash
# CUDA 11.8（兼容性最好，推荐）
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 或 CUDA 12.1（最新版本，需要较新显卡）
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**安装前确认：**

1. ✅ 已安装 NVIDIA 显卡驱动（版本 ≥ 450.80.02）
2. ✅ 已安装 CUDA Toolkit（版本需与PyTorch匹配）
3. ✅ Python版本为 3.8-3.11

**验证GPU是否可用：**

```bash
python -c "import torch; print(f'CUDA可用: {torch.cuda.is_available()}'); print(f'GPU名称: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"无\"}')"
```

**CPU模式（无GPU时）：**

如果没有NVIDIA GPU或不需要GPU加速，可以跳过此步骤，直接使用CPU模式运行。

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

## 核心逻辑详解

### 1. 主程序入口逻辑（main.py）

#### 1.1 评估流程

```
步骤1: 读取简历文件 → 步骤2: 解析评估标准 → 步骤3: 评估候选人 → 步骤4: 处理结果 → 步骤5: 生成Excel
```

#### 1.2 评估模式选择

根据命令行参数决定评估方式：

```python
if use_local:
    # 使用本地模型
    prompt = build_evaluation_prompt(candidate, position_key, use_local=True)
    response = call_local_model(prompt)
elif use_llm:
    # 使用远程模型
    prompt = build_evaluation_prompt(candidate, position_key, use_local=False)
    response = call_llm_api(prompt)
else:
    # 规则匹配兜底（简单关键词匹配）
```

#### 1.3 规则匹配兜底逻辑

当LLM评估失败时，使用简单关键词匹配：

```
1. 获取岗位评估标准中的所有达标项
2. 在简历全文中搜索这些达标项
3. 匹配分数 = (匹配项数 / 总项数) × 100
4. 根据分数确定优先级：
   - ≥85分 → P0（优先推荐）
   - ≥70分 → P1（推荐）
   - ≥50分 → P2（备选）
   - <50分 → P3（暂不推荐）
```

---

### 2. 配置模块逻辑（config.py）

#### 2.1 配置结构

配置文件按模块分类：

| 配置项 | 用途 | 关键字段 |
|--------|------|----------|
| `COMMON_CONFIG` | 通用配置 | 数据路径、优先级定义、评估维度 |
| `LLM_CONFIG` | 远程大模型配置 | api_base、api_key、model、temperature |
| `LOCAL_LLM_CONFIG` | 本地大模型配置 | model_path、model_name、hf_mirror、load_in_4bit |

#### 2.2 评估维度配置

每个岗位可配置独立的评估维度：

```python
EVALUATION_DIMENSIONS = {
    '前端': [
        {'id': 'D1', 'name': '核心技术栈匹配度', 'weight': 30, 'standard': '精通Vue3+TypeScript...'},
        {'id': 'D2', 'name': '经验年限与学历', 'weight': 20, 'standard': '本科及以上...'},
        # ...
    ],
    # 其他岗位配置...
}
```

- **权重**：各维度权重之和应为100%
- **标准**：达标标准会被拆分为多个子项用于动态权重计算

---

### 3. 远程大模型模块逻辑（llm/remote_llm.py）

#### 3.1 Prompt构建逻辑

完整评估Prompt由四部分组成：

```
评估标准文本 (criteria_text)
+ 动态权重计算规则 (dynamic_weight_text)
+ 候选人信息 (build_candidate_info_text)
+ 评估指令 (EVALUATION_INSTRUCTION)
```

**动态权重计算规则**：根据每个维度的达标项数量计算单项分数：

```
每个评估维度的权重将按照其达标标准中的项目数量进行动态分配：
  D1. 核心技术栈匹配度（权重30%）：5个达标项，每项6%
    1. 精通Vue3+TypeScript
    2. 理解框架底层原理
    ...
```

#### 3.2 API调用逻辑

使用OpenAI兼容的Chat Completions API格式：

```python
payload = {
    'model': 'qwen-max',
    'messages': [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': prompt}
    ],
    'temperature': 0.1,
    'max_tokens': 2000
}
```

**重试机制**：支持自动重试（最多3次），采用指数退避策略（等待时间逐次翻倍）。

#### 3.3 响应解析逻辑

支持多种解析方式，层层递进：

```
1. 去除markdown代码块标记（```json ... ```）
2. 去除思维链标签（<think>...</think>）
3. 使用正则提取JSON块
4. 尝试JSON解析
   ├─ 成功 → 提取评估结果字段
   └─ 失败 → 正则表达式提取关键信息（匹配度、优先级、优势、风险等）
5. 若match_score > 0 → 返回结果，否则返回None
```

---

### 4. 本地大模型模块逻辑（local_llm/local_model.py）

#### 4.1 GPU检测逻辑

```python
if torch.cuda.is_available():
    return 'cuda'  # NVIDIA GPU
elif torch.backends.mps.is_available():
    return 'mps'   # Apple Silicon
else:
    return 'cpu'   # CPU
```

#### 4.2 模型加载策略

```
1. 检查 model_path/模型名/ 目录是否存在且有模型文件
   ├─ 存在 → 直接从本地加载
   └─ 不存在 → 检查 model_path 根目录是否有模型文件
      ├─ 存在 → 从根目录加载（兼容旧结构）
      └─ 不存在 → 使用model_name从HuggingFace镜像自动下载
2. 下载后自动保存到 model_path/模型名/ 目录
3. 下次直接从本地加载，无需重复下载
```

#### 4.3 模型名称映射

支持简写名称自动转换为完整HuggingFace ID：

| 简写 | 完整ID |
|------|--------|
| `qwen2-7b-instruct` | `Qwen/Qwen2-7B-Instruct` |
| `qwen2-1.5b-instruct` | `Qwen/Qwen2-1.5B-Instruct` |
| `qwen2.5-7b-instruct` | `Qwen/Qwen2.5-7B-Instruct` |

#### 4.4 4-bit量化加载

当 `load_in_4bit=True` 且设备为CUDA时，使用BitsAndBytesConfig进行4-bit量化，大幅减少显存占用。

---

### 5. 资源管理模块逻辑（utils/resource_manager.py）

#### 5.1 资源发现逻辑

扫描三个目录发现可用资源：

```python
resources = {
    'positions': {},      # 岗位名 -> 详细信息
    'resume_dirs': {},    # 简历目录（原始目录名）
    'eval_docs': {},      # 评估标准文件
    'rule_files': {}      # 规则文件
}
```

#### 5.2 LLM智能匹配逻辑

根据当前评估模式选择远程或本地LLM进行语义匹配：

```python
if _use_local_llm:
    response = _call_local_llm_for_match(prompt)
else:
    response = _call_remote_llm_for_match(prompt)
```

#### 5.3 本地模糊匹配算法（三层递进）

当LLM匹配失败时，回退到本地模糊匹配：

**第1层：精确匹配（不区分大小写）**

```python
for resource in resources.keys():
    if resource.lower() == input_lower:
        return resource
```

**第2层：包含匹配（按质量排序）**

```
- 正向包含：输入是资源名的子串（更常见）
  - 匹配位置越靠前，权重越高（前缀匹配权重×1.5）
  - 匹配比例越高，得分越高
- 反向包含：资源名是输入的子串（可能误匹配）
  - 给予0.6倍惩罚权重
- 所有匹配按得分排序，返回最高分
```

**第3层：相似度匹配（综合评分）**

```
综合得分 = 0.5 × 编辑距离相似度 + 0.35 × 加权字符重叠度 + 前缀匹配加分

1. 编辑距离相似度（SequenceMatcher）：计算字符串相似度
2. 加权字符重叠度：开头字符权重更高（1.0 → 0.5线性衰减）
3. 前缀匹配加分：
   - 资源名以输入前2字符开头 → +0.15
   - 以输入前3字符开头 → +0.10（额外）
   - 以输入前4字符开头 → +0.05（额外）
   - 最大加分0.30
4. 阈值：综合得分 ≥ 0.5 才视为有效匹配
```

**示例**：输入"前端开发"匹配"前端测试人员" vs "后端开发人员"

| 资源 | 编辑距离 | 加权重叠度 | 前缀加分 | 综合得分 |
|------|----------|------------|----------|----------|
| 前端测试人员 | 0.400 | 0.577 | 0.200 | 0.602 ✅ |
| 后端开发人员 | 0.600 | 0.692 | 0.000 | 0.542 ❌ |

---

### 6. 简历读取模块逻辑（utils/resume_reader.py）

#### 6.1 PDF文本提取逻辑

```
优先使用PyMuPDF（fitz）解析PDF：
  ├─ 成功 → 返回提取的文本
  └─ 失败 → 回退到PyPDF2解析
     ├─ 成功 → 返回提取的文本
     └─ 失败 → 返回空字符串，记录错误日志
```

#### 6.2 文件名解析逻辑

支持多种文件名格式：

```python
# 格式1: 【前端开发工程师_北京 8-12K】于宗源 4年.pdf
pattern: 【(.+?)】(.+?)\s*(\d+年|10年以上)

# 格式2: 于宗源 4年.pdf
pattern: (.+?)\s*(\d+年|10年以上)

# 格式3: 张三.pdf
直接取文件名（不含扩展名）作为姓名
```

#### 6.3 候选人信息提取逻辑

使用正则表达式从简历文本中提取：

| 字段 | 正则模式 |
|------|----------|
| 手机号 | `1[3-9]\d{9}` |
| 性别 | `(男|女)` |
| 年龄 | `(\d{1,2})\s*岁` 或出生年份计算 |
| 学历 | `(本科|硕士|大专|专科|博士)` |
| 技能 | `(技能|专业技能|核心技能)\s*[:：]\s*([^\n\r]+)` |
| 项目经验 | `(项目经验|工作经历)\s*[:：]?\s*([\s\S]*?)(?=\n\n|\Z)` |
| 个人简介 | `(个人简介|自我评价)\s*[:：]?\s*([\s\S]*?)(?=\n\n|\Z)` |

#### 6.4 自动发现岗位逻辑

扫描 `RESUMES_PATH` 目录下的所有子目录，每个子目录代表一个岗位类型：

```python
for item in os.listdir(RESUMES_PATH):
    item_path = os.path.join(RESUMES_PATH, item)
    if os.path.isdir(item_path):
        position_dirs[item] = item_path
```

---

### 7. 评估标准解析模块逻辑（utils/evaluation_parser.py）

#### 7.1 Excel文件解析逻辑

遍历Excel中的所有工作表，根据表头内容判断表格类型：

```python
if '评估维度' in header_str:
    # 解析评估维度表格
    for row in rows[1:]:
        # 提取维度ID、名称、权重、标准
        # 将标准拆分为达标项列表
        
elif '等级' in header_str or '优先级' in header_str:
    # 解析优先级等级表格（行数<=6且尚未提取过）
    for row in rows[1:]:
        if level in ['P0', 'P1', 'P2', 'P3']:
            # 提取等级、含义、分数范围、建议动作
```

#### 7.2 标准项拆分逻辑

将评估标准字符串拆分为达标项列表：

```python
items = re.split(r'[,，;；、。\n]+', standard)
for item in items:
    item = item.strip()
    if item and len(item) > 2:
        standard_items.append(item)
```

#### 7.3 缓存机制

已解析的评估标准会缓存到 `_criteria_cache`，避免重复读取和解析。

---

### 8. 数据处理模块逻辑（utils/data_processor.py）

#### 8.1 排序逻辑

```python
sorted_list = sorted(
    candidates,
    key=lambda c: (
        priority_map.get(c.get('priority', 'P3'), 4),  # 优先级排序（P0 < P1 < P2 < P3）
        -c.get('match_score', 0)                       # 同优先级按匹配度降序
    )
)
```

#### 8.2 分组逻辑

按优先级等级分组，每组内按匹配度降序排列：

```python
grouped = {p: [] for p in PRIORITY_ORDER}  # {'P0': [], 'P1': [], 'P2': [], 'P3': []}

for candidate in candidates:
    priority = candidate.get('priority', 'P3')
    grouped[priority].append(candidate)

# 每组内排序
for priority in grouped:
    grouped[priority] = sorted(grouped[priority], key=lambda c: -c.get('match_score', 0))
```

#### 8.3 排名逻辑

为排序后的候选人依次添加排名序号：

```python
for i, candidate in enumerate(candidates, 1):
    candidate['rank'] = i
```

#### 8.4 统计逻辑

计算各优先级等级的人数分布：

```python
distribution = {p: 0 for p in PRIORITY_ORDER}
distribution['total'] = len(candidates)

for candidate in candidates:
    priority = candidate.get('priority', 'P3')
    if priority in distribution:
        distribution[priority] += 1
```

#### 8.5 报告生成逻辑

将处理后的结果格式化为文本报告，包含每个岗位的统计和汇总统计。

---

### 9. Excel输出模块逻辑（utils/excel_writer.py）

#### 9.1 列宽计算逻辑

```python
# 基础宽度 = 中文字符数 × 1.5 + 英文字符数 × 0.9
# 特殊列设置固定宽度（如手机号15、核心亮点45等）
# 最小宽度8，最大宽度60
```

#### 9.2 样式应用逻辑

**表头样式**：
- 字体：微软雅黑、加粗、黑色、11号
- 填充：浅绿色背景（RGB: 152, 215, 182）
- 对齐：居中对齐、自动换行
- 边框：细边框

**数据行样式**：
- 奇偶行条纹效果（奇数行白色、偶数行浅灰色）
- 文本左对齐、数字/匹配度/优先级居中对齐
- 行高根据内容长度自动调整（20-35像素）

**优先级着色**：

| 优先级 | 背景色 | 字体颜色 |
|--------|--------|----------|
| P0 | 深绿色（548235） | 白色加粗 |
| P1 | 深黄色（BF9000） | 白色加粗 |
| P2 | 深橙色（C00000） | 白色加粗 |
| P3 | 绿色（70AD47） | 白色加粗 |

**匹配度着色**：

| 匹配度 | 背景色 | 字体颜色 |
|--------|--------|----------|
| ≥80% | 浅绿色（C6EFCE） | 深绿色加粗 |
| 60-80% | 浅黄色（FFEB9C） | 深黄色加粗 |
| <60% | 浅红色（FFC7CE） | 深红色加粗 |

#### 9.3 模板加载逻辑

如果存在模板文件（`OUTPUT_TEMPLATE_PATH`），则加载模板并清空数据行，保持格式一致性；否则创建新工作簿。

#### 9.4 文件保存重试机制

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        wb.save(filepath)
        return filepath
    except PermissionError:
        if attempt < max_retries - 1:
            time.sleep(1)
            continue
        else:
            raise
```

---

### 10. 提示词模板模块逻辑（utils/prompt_templates.py）

#### 10.1 模板列表

| 模板 | 类型 | 用途 |
|------|------|------|
| `RESOURCE_MATCH_SYSTEM_PROMPT` | 常量 | 资源匹配的system_prompt |
| `EVALUATION_SYSTEM_PROMPT` | 常量 | 简历评估的system_prompt |
| `build_resource_match_prompt()` | 函数 | 构建资源匹配提示词 |
| `build_candidate_info_text()` | 函数 | 构建候选人信息展示文本 |
| `EVALUATION_INSTRUCTION` | 常量 | 远程模型评估指令+JSON输出格式 |
| `LOCAL_EVALUATION_INSTRUCTION` | 常量 | 本地模型评估指令（简化格式） |

#### 10.2 资源匹配提示词结构

```
你是一个智能匹配助手，需要将用户的输入与系统中的资源进行匹配。

用户输入: {user_input}

系统中的{resource_type}资源列表:
1. {resource1}
2. {resource2}
...

请根据语义相似度，返回最匹配的资源名称。
只返回资源名称，不要其他解释。
如果不确定，返回空字符串。
```

#### 10.3 评估指令结构

要求大模型按JSON格式输出评估结果，包含以下字段：

```json
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
    "preliminary_info": "综合信息",
    "dimension_scores": {"D1": 70, "D2": 75, "D3": 68, "D4": 72},
    "dimension_details": {...}
}
```

---



---

## 错误处理机制

### 各模块错误处理策略

| 模块 | 错误类型 | 处理策略 | 返回值 |
|------|----------|----------|--------|
| `resume_reader.py` | PDF解析失败 | 记录错误日志，跳过该文件 | 空字符串 |
| `resume_reader.py` | 文件名解析失败 | 记录错误日志，使用文件名作为姓名 | 文件名（不含扩展名） |
| `evaluation_parser.py` | Excel文件不存在 | 记录错误日志，返回空标准 | `{dimensions: [], priority_levels: []}` |
| `evaluation_parser.py` | Excel解析失败 | 记录错误日志，返回空标准 | `{dimensions: [], priority_levels: []}` |
| `remote_llm.py` | API配置不完整 | 记录警告日志，回退到规则评估 | `None` |
| `remote_llm.py` | API调用超时 | 自动重试（最多3次），指数退避 | `None` |
| `remote_llm.py` | API调用失败 | 自动重试（最多3次），指数退避 | `None` |
| `remote_llm.py` | 响应解析失败 | 记录警告日志，尝试正则提取 | `None` |
| `local_model.py` | GPU检测失败 | 记录警告日志，使用CPU | CPU设备信息 |
| `local_model.py` | 模型加载失败 | 记录错误日志，返回失败状态 | `False` |
| `local_model.py` | 模型推理失败 | 记录错误日志，返回None | `None` |
| `excel_writer.py` | 文件保存权限不足 | 自动重试（最多3次，间隔1秒） | 抛出异常 |
| `resource_manager.py` | LLM匹配失败 | 自动回退到本地模糊匹配 | 匹配结果或None |

### API调用重试机制

```python
# remote_llm.py 中的重试逻辑
max_retries = 3
timeout = (15, 120)

for attempt in range(max_retries):
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        time.sleep(2 * (attempt + 1))
    except Exception as e:
        time.sleep(2 * (attempt + 1))
```

### 文件保存重试机制

```python
# excel_writer.py 中的保存重试逻辑
max_retries = 3
for attempt in range(max_retries):
    try:
        wb.save(filepath)
        return filepath
    except PermissionError:
        if attempt < max_retries - 1:
            time.sleep(1)
            continue
        else:
            raise
```

### 评估失败兜底逻辑

```python
# main.py 中的评估失败兜底
if llm_response:
    result = parse_llm_response(response)
    if result:
        return result

# LLM评估失败，使用规则匹配兜底
match_score = (matched_count / total_items) * 100
priority = determine_priority(match_score)
return {
    'match_score': match_score,
    'priority': priority,
    'core_strengths': f"匹配了 {matched_count}/{total_items} 个评估项",
}
```

---

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
    'priority_levels': {...}
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
- **背景色**：浅绿色（RGB: 152, 215, 182）
- **字体**：微软雅黑、加粗、黑色、11号字
- **对齐**：居中对齐、垂直居中、自动换行
- **行高**：28像素

#### 数据行样式
- **奇偶行条纹效果**：奇数行白色背景、偶数行浅灰色背景（#F2F2F2）
- **对齐方式**：文本左对齐、数字/匹配度/优先级居中对齐
- **行高**：根据内容长度自动调整（20-35像素）

#### 优先级着色
| 优先级 | 背景色 | 字体颜色 |
|--------|--------|----------|
| P0 | 深绿色（548235） | 白色加粗 |
| P1 | 深黄色（BF9000） | 白色加粗 |
| P2 | 深橙色（C00000） | 白色加粗 |
| P3 | 绿色（70AD47） | 白色加粗 |

#### 匹配度着色
| 匹配度 | 背景色 | 字体颜色 |
|--------|--------|----------|
| ≥80% | 浅绿色（C6EFCE） | 深绿色加粗 |
| 60-80% | 浅黄色（FFEB9C） | 深黄色加粗 |
| <60% | 浅红色（FFC7CE） | 深红色加粗 |

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

**处理**：需要在 `data/AssessmentCriteria/` 目录下添加对应的评估标准Excel文件，否则评估标准为空，系统将使用规则匹配进行评估

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