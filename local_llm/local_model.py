"""
简历智能评估系统 - 本地模型模块

该模块负责加载和使用本地大模型进行评估，支持GPU加速。

核心功能：
1. GPU检测：检测电脑是否有可用的GPU
2. 模型加载：优先从本地路径加载，本地不存在时自动从HuggingFace镜像下载
3. 模型推理：使用本地模型进行推理
4. 设备管理：自动选择GPU或CPU

模型加载策略：
1. 如果model_path/模型名/ 目录存在且有模型文件 → 直接从本地加载
2. 如果目录不存在 → 用model_name从HuggingFace镜像自动下载
3. 下载后自动保存到model_path/模型名/ 目录，下次直接从本地加载

镜像配置：
- 通过config.hf_mirror设置HuggingFace镜像地址（国内推荐 https://hf-mirror.com）
- 通过os.environ设置HF_ENDPOINT环境变量，transformers库会自动使用

使用依赖：
- torch：PyTorch深度学习框架
- transformers：Hugging Face模型库（AutoModelForCausalLM, AutoTokenizer）
- accelerate：模型加速库
- bitsandbytes：4bit量化支持（可选）
- logging：日志记录
"""

import logging
import os
from utils.prompt_templates import EVALUATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

torch = None
AutoModelForCausalLM = None
AutoTokenizer = None
BitsAndBytesConfig = None


def _setup_hf_mirror(mirror_url):
    """
    设置HuggingFace镜像环境变量
    
    通过设置HF_ENDPOINT环境变量，让transformers库从镜像站下载模型。
    国内网络环境下必须设置，否则无法访问huggingface.co。
    
    Args:
        mirror_url: 镜像地址，如 'https://hf-mirror.com'
    """
    if mirror_url:
        os.environ['HF_ENDPOINT'] = mirror_url.rstrip('/')
        logger.info(f"已设置HuggingFace镜像: {os.environ['HF_ENDPOINT']}")


def init_torch():
    """
    延迟初始化PyTorch相关库
    
    只有在需要使用本地模型时才加载PyTorch，避免不必要的内存占用
    """
    global torch

    if torch is None:
        try:
            import torch
            logger.info("成功加载PyTorch库")
            return True
        except ImportError as e:
            logger.error(f"加载PyTorch库失败: {e}")
            logger.error("请安装PyTorch: pip install torch")
            return False

    return True


def init_transformers():
    """
    延迟初始化transformers库
    
    只有在需要使用本地模型进行推理时才加载transformers
    """
    global AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    if AutoModelForCausalLM is None:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            logger.info("成功加载transformers库")
            try:
                from transformers import BitsAndBytesConfig
                logger.info("成功加载BitsAndBytesConfig")
            except ImportError:
                BitsAndBytesConfig = None
                logger.warning("BitsAndBytesConfig不可用，4bit量化将不可用")
            return True
        except ImportError as e:
            logger.error(f"加载transformers库失败: {e}")
            logger.error("请安装transformers: pip install transformers accelerate")
            return False

    return True


def detect_gpu():
    """
    检测电脑是否有可用的GPU
    
    Returns:
        dict: GPU检测结果
            - has_gpu: bool, 是否有可用GPU
            - device_type: str, 设备类型 ('cuda'或'cpu')
            - gpu_name: str, GPU名称（如果有）
            - gpu_count: int, GPU数量
            - gpu_memory: str, GPU显存信息（如果有）
    """
    if not init_torch():
        return {
            'has_gpu': False,
            'device_type': 'cpu',
            'gpu_name': '',
            'gpu_count': 0,
            'gpu_memory': ''
        }
    
    result = {
        'has_gpu': False,
        'device_type': 'cpu',
        'gpu_name': '',
        'gpu_count': 0,
        'gpu_memory': ''
    }
    
    if torch.cuda.is_available():
        result['has_gpu'] = True
        result['device_type'] = 'cuda'
        result['gpu_count'] = torch.cuda.device_count()
        
        try:
            result['gpu_name'] = torch.cuda.get_device_name(0)
        except Exception as e:
            logger.warning(f"获取GPU名称失败: {e}")
            result['gpu_name'] = 'Unknown'
        
        try:
            total_mem = torch.cuda.get_device_properties(0).total_memory
            result['gpu_memory'] = f"{total_mem // (1024**3)}GB"
        except Exception as e:
            logger.warning(f"获取GPU显存失败: {e}")
            result['gpu_memory'] = 'Unknown'
        
        logger.info(f"检测到GPU: {result['gpu_name']}, 显存: {result['gpu_memory']}, 数量: {result['gpu_count']}")
    
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        result['has_gpu'] = True
        result['device_type'] = 'mps'
        result['gpu_name'] = 'Apple Silicon (MPS)'
        
        logger.info("检测到Apple Silicon GPU")
    
    else:
        logger.info("未检测到GPU，将使用CPU")
    
    return result


def get_device():
    """
    获取最佳可用设备
    
    Returns:
        str: 设备标识 ('cuda', 'mps', 或 'cpu')
    """
    if not init_torch():
        return 'cpu'
    
    if torch.cuda.is_available():
        return 'cuda'
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return 'mps'
    else:
        return 'cpu'


class LocalModel:
    """
    本地大模型封装类
    
    负责加载本地模型并提供推理接口，支持GPU加速。
    
    Attributes:
        model: 加载的模型对象
        tokenizer: 分词器对象
        device: 使用的设备 ('cuda', 'mps', 或 'cpu')
        config: 模型配置
    """
    
    def __init__(self, config):
        """
        初始化本地模型
        
        Args:
            config: 模型配置字典，包含model_path, model_name等参数
        """
        self.config = config
        self.model = None
        self.tokenizer = None
        self.device = get_device()
        self.is_loaded = False
        
        logger.info(f"本地模型配置: {config.get('model_name')}, 设备: {self.device}")
    
    def _get_model_local_dir(self):
        """
        获取模型在本地存放的目录路径
        
        目录结构: model_path / 模型短名 /
        例如: D:\Project\BossData2\model\Qwen2-7B-Instruct\
        
        不同模型会存放在不同子目录下，互不干扰。
        
        Returns:
            str: 模型本地目录的绝对路径
        """
        model_path = self.config.get('model_path', '')
        model_name = self.config.get('model_name', '')
        hf_model_id = self._to_hf_model_id(model_name)
        short_name = hf_model_id.split('/')[-1]
        return os.path.join(model_path, short_name)
    
    def _resolve_model_id(self):
        """
        解析模型标识，决定从哪里加载模型
        
        加载策略：
        1. 先检查model_path/模型名/ 目录是否存在且有模型文件 → 直接从本地加载
        2. 再检查model_path目录本身是否有模型文件 → 直接从本地加载（兼容旧结构）
        3. 都没有 → 使用model_name从HuggingFace镜像自动下载
        
        Returns:
            str: 模型标识（本地路径或HuggingFace模型ID），失败返回None
        """
        model_name = self.config.get('model_name', '')
        model_path = self.config.get('model_path', '')
        
        model_local_dir = self._get_model_local_dir()
        
        if model_local_dir and os.path.isdir(model_local_dir):
            if self._dir_has_model(model_local_dir):
                logger.info(f"检测到本地模型目录: {model_local_dir}")
                return model_local_dir
            else:
                logger.warning(f"本地目录 {model_local_dir} 存在但未找到模型文件，将尝试从HuggingFace下载")
        
        if model_path and os.path.isdir(model_path):
            if self._dir_has_model(model_path):
                logger.info(f"检测到本地模型目录(根目录): {model_path}")
                return model_path
        
        if not model_name:
            logger.error("本地模型目录不存在且未配置model_name，无法加载模型")
            return None
        
        hf_model_id = self._to_hf_model_id(model_name)
        logger.info(f"本地模型目录不存在，将从HuggingFace镜像下载: {hf_model_id}")
        logger.info(f"下载后将保存到: {model_local_dir}")
        return hf_model_id
    
    @staticmethod
    def _dir_has_model(directory):
        """
        检查目录中是否包含模型文件
        
        Args:
            directory: 目录路径
            
        Returns:
            bool: 是否包含模型文件
        """
        try:
            files = os.listdir(directory)
            has_model_file = any(f.endswith(('.safetensors', '.bin', '.pt')) for f in files)
            has_config = 'config.json' in files
            return has_model_file or has_config
        except OSError:
            return False
    
    @staticmethod
    def _to_hf_model_id(model_name):
        """
        将简短模型名转换为HuggingFace模型ID
        
        支持的简短名称映射：
        - qwen2-7b-instruct → Qwen/Qwen2-7B-Instruct
        - qwen2.5-7b-instruct → Qwen/Qwen2.5-7B-Instruct
        - 等等
        
        如果已经是完整的HuggingFace ID（包含/），则直接返回。
        
        Args:
            model_name: 模型名称
            
        Returns:
            str: HuggingFace模型ID
        """
        if '/' in model_name:
            return model_name
        
        name_map = {
            'qwen2-7b-instruct': 'Qwen/Qwen2-7B-Instruct',
            'qwen2-1.5b-instruct': 'Qwen/Qwen2-1.5B-Instruct',
            'qwen2-0.5b-instruct': 'Qwen/Qwen2-0.5B-Instruct',
            'qwen2-72b-instruct': 'Qwen/Qwen2-72B-Instruct',
            'qwen2.5-7b-instruct': 'Qwen/Qwen2.5-7B-Instruct',
            'qwen2.5-3b-instruct': 'Qwen/Qwen2.5-3B-Instruct',
            'qwen2.5-1.5b-instruct': 'Qwen/Qwen2.5-1.5B-Instruct',
            'qwen2.5-0.5b-instruct': 'Qwen/Qwen2.5-0.5B-Instruct',
            'qwen2.5-14b-instruct': 'Qwen/Qwen2.5-14B-Instruct',
            'qwen2.5-72b-instruct': 'Qwen/Qwen2.5-72B-Instruct',
        }
        
        resolved = name_map.get(model_name.lower())
        if resolved:
            return resolved
        
        logger.warning(f"未识别的模型名: {model_name}，将作为HuggingFace ID直接使用")
        return model_name

    def load_model(self):
        """
        加载本地模型
        
        加载策略：
        1. 优先从本地model_path/模型名/ 目录加载
        2. 本地目录不存在时，用model_name从HuggingFace镜像自动下载
        3. 下载后自动保存到model_path/模型名/ 目录，下次直接从本地加载
        
        支持GPU加速（如果可用），支持4bit量化加载节省显存。
        
        Returns:
            bool: 是否加载成功
        """
        if self.is_loaded:
            logger.info("模型已加载，跳过")
            return True
        
        if not init_torch():
            logger.error("PyTorch未加载，无法加载模型")
            return False
        
        if not init_transformers():
            logger.error("transformers库未加载，无法加载模型")
            return False
        
        hf_mirror = self.config.get('hf_mirror', '')
        _setup_hf_mirror(hf_mirror)
        
        model_id = self._resolve_model_id()
        if not model_id:
            return False
        
        is_from_hf = '/' in model_id and not os.path.isdir(model_id)
        model_local_dir = self._get_model_local_dir()
        
        try:
            logger.info(f"开始加载模型: {model_id}")
            
            logger.info("加载分词器...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                trust_remote_code=self.config.get('trust_remote_code', True)
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            logger.info("加载模型...")
            
            load_kwargs = {
                'pretrained_model_name_or_path': model_id,
                'trust_remote_code': self.config.get('trust_remote_code', True),
                'device_map': self.config.get('device_map', 'auto')
            }
            
            if self.config.get('load_in_4bit', True) and self.device == 'cuda':
                if BitsAndBytesConfig is not None:
                    load_kwargs['quantization_config'] = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_quant_type="nf4"
                    )
                    logger.info("使用4bit量化加载模型（BitsAndBytesConfig）")
                else:
                    load_kwargs['torch_dtype'] = torch.float16
                    logger.warning("BitsAndBytesConfig不可用，使用float16加载（显存占用更大）")
            else:
                load_kwargs['torch_dtype'] = torch.float16
                logger.info("使用float16加载模型")
            
            self.model = AutoModelForCausalLM.from_pretrained(**load_kwargs)
            
            if is_from_hf and model_local_dir:
                os.makedirs(model_local_dir, exist_ok=True)
                logger.info(f"正在保存模型到本地目录: {model_local_dir}")
                self.tokenizer.save_pretrained(model_local_dir)
                self.model.save_pretrained(model_local_dir)
                logger.info(f"模型已保存到: {model_local_dir}，下次将直接从本地加载")
            
            if self.device == 'cuda':
                logger.info(f"模型已加载到GPU: {torch.cuda.get_device_name(0)}")
            elif self.device == 'mps':
                logger.info("模型已加载到Apple Silicon GPU")
            else:
                logger.info("模型已加载到CPU")
            
            self.is_loaded = True
            logger.info("模型加载成功")
            
            return True
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            logger.error("请检查模型名称是否正确，或网络是否可访问HuggingFace镜像")
            return False

    def generate(self, prompt, max_tokens=None, temperature=None):
        """
        使用本地模型生成响应

        Args:
            prompt: 输入提示文本
            max_tokens: 最大生成token数（可选，默认使用配置）
            temperature: 温度参数（可选，默认使用配置）

        Returns:
            str: 模型生成的响应文本，失败返回None
        """
        if not self.is_loaded:
            logger.error("模型未加载，请先调用load_model()")
            return None

        try:
            max_tokens = max_tokens or self.config.get('max_tokens', 2000)
            temperature = temperature or self.config.get('temperature', 0.1)
            max_input_length = self.config.get('max_input_length', 4096)
            system_prompt = self.config.get('system_prompt', EVALUATION_SYSTEM_PROMPT)

            messages = [
                {
                    'role': 'system',
                    'content': system_prompt
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ]

            input_text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )

            inputs = self.tokenizer(
                input_text,
                return_tensors='pt',
                padding=True,
                truncation=True,
                max_length=max_input_length
            ).to(self.device)

            logger.info(f"开始生成响应（max_tokens={max_tokens}, temperature={temperature}）")

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=self.config.get('top_p', 0.9),
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )

            response = self.tokenizer.decode(
                outputs[0][len(inputs.input_ids[0]):],
                skip_special_tokens=True
            )

            logger.info(f"响应生成完成，长度: {len(response)}")

            return response.strip()

        except Exception as e:
            logger.error(f"模型推理失败: {e}")
            return None


_global_model = None


def get_local_model(config=None):
    """
    获取全局本地模型实例（单例模式）

    Args:
        config: 模型配置（可选，首次调用时需要）

    Returns:
        LocalModel: 本地模型实例
    """
    global _global_model

    if _global_model is None:
        from config import LOCAL_LLM_CONFIG
        _global_model = LocalModel(config or LOCAL_LLM_CONFIG)

    return _global_model


def call_local_model(prompt, config=None):
    """
    调用本地模型生成响应

    这是一个便捷函数，会自动加载模型并生成响应。

    Args:
        prompt: 输入提示文本
        config: 模型配置（可选）

    Returns:
        str: 模型生成的响应文本，失败返回None
    """
    model = get_local_model(config)

    if not model.is_loaded:
        if not model.load_model():
            return None

    return model.generate(prompt)