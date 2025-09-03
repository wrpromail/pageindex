#!/usr/bin/env python3
"""
模型管理器 - 管理多个模型的配置和调用
"""

import os
import yaml
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from openai import OpenAI

@dataclass
class ModelConfig:
    """模型配置类"""
    name: str
    description: str
    api_key: str
    base_url: str
    model_name: str
    max_tokens: int
    context_limit: int
    temperature: float
    enabled: bool

@dataclass
class CallStats:
    """调用统计"""
    total_calls: int = 0
    total_tokens: int = 0
    total_time: float = 0.0
    success_calls: int = 0
    failed_calls: int = 0

class ModelManager:
    """模型管理器"""
    
    def __init__(self, config_file: str = "model_configs.yaml"):
        self.config_file = config_file
        self.models: Dict[str, ModelConfig] = {}
        self.scenarios: Dict[str, Dict] = {}
        self.directories: Dict[str, str] = {}
        self.defaults: Dict = {}
        self.indexing: Dict = {}
        self.stats: Dict[str, CallStats] = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 清空现有配置
            self.models.clear()
            self.scenarios.clear()
            self.directories.clear()
            self.defaults.clear()
            self.indexing.clear()
            # 注意：保留stats，因为这是运行时统计信息

            # 加载模型配置
            for model_id, model_config in config.get('models', {}).items():
                # 处理环境变量
                api_key = self._resolve_env_var(model_config['api_key'])
                if api_key:
                    # 使用name字段作为model_name（简化后的配置）
                    model_name = model_config['name']
                    self.models[model_id] = ModelConfig(
                        name=model_name,
                        description=model_config.get('description', model_name),
                        api_key=api_key,
                        base_url=model_config['base_url'],
                        model_name=model_name,  # 直接使用name字段
                        max_tokens=model_config['max_tokens'],
                        context_limit=model_config['context_limit'],
                        temperature=model_config.get('temperature', 0.1),
                        enabled=True  # 所有配置的模型都启用
                    )
                    # 只为新模型初始化统计信息
                    if model_id not in self.stats:
                        self.stats[model_id] = CallStats()
            
            # 加载场景配置
            self.scenarios = config.get('scenarios', {})
            
            # 加载目录配置
            self.directories = config.get('directories', {})
            
            # 加载默认配置
            self.defaults = config.get('defaults', {})
            
            # 加载索引配置
            self.indexing = config.get('indexing', {})
            
            print(f"✅ 已加载 {len(self.models)} 个启用的模型")
            
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            raise
    
    def _resolve_env_var(self, value: str) -> Optional[str]:
        """解析环境变量"""
        if value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            return os.getenv(env_var)
        return value
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """获取可用模型列表"""
        return [
            {
                'id': model_id,
                'name': model.name,
                'description': model.description,
                'context_limit': model.context_limit,
                'max_tokens': model.max_tokens
            }
            for model_id, model in self.models.items()
        ]
    
    def get_indexing_config(self):
        """获取索引配置"""
        return self.indexing
    
    def get_available_scenarios(self) -> List[Dict[str, str]]:
        """获取可用场景列表"""
        return [
            {
                'id': scenario_id,
                'name': scenario['name'],
                'description': scenario['description']
            }
            for scenario_id, scenario in self.scenarios.items()
        ]
    
    def get_model_config(self, model_id: str) -> Optional[ModelConfig]:
        """获取模型配置"""
        return self.models.get(model_id)
    
    def create_client(self, model_id: str) -> Optional[OpenAI]:
        """创建OpenAI客户端"""
        model_config = self.get_model_config(model_id)
        if not model_config:
            return None
        
        return OpenAI(
            api_key=model_config.api_key,
            base_url=model_config.base_url
        )
    
    def call_model(self, model_id: str, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """调用模型并记录统计信息"""
        model_config = self.get_model_config(model_id)
        if not model_config:
            return {'error': f'模型 {model_id} 不存在或未启用'}
        
        client = self.create_client(model_id)
        if not client:
            return {'error': f'无法创建模型 {model_id} 的客户端'}
        
        # 准备调用参数
        call_params = {
            'model': model_config.model_name,
            'messages': messages,
            'max_tokens': model_config.max_tokens,
            'temperature': model_config.temperature,
            **kwargs
        }
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            response = client.chat.completions.create(**call_params)
            
            # 计算耗时
            elapsed_time = time.time() - start_time
            
            # 更新统计信息
            stats = self.stats[model_id]
            stats.total_calls += 1
            stats.success_calls += 1
            stats.total_time += elapsed_time
            
            # 尝试获取token使用量
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0
            
            if hasattr(response, 'usage') and response.usage:
                input_tokens = getattr(response.usage, 'prompt_tokens', 0)
                output_tokens = getattr(response.usage, 'completion_tokens', 0)
                total_tokens = getattr(response.usage, 'total_tokens', 0)
                stats.total_tokens += total_tokens
            
            return {
                'success': True,
                'content': response.choices[0].message.content,
                'model': model_config.model_name,
                'elapsed_time': elapsed_time,
                'tokens_used': total_tokens,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'stats': {
                    'total_calls': stats.total_calls,
                    'success_calls': stats.success_calls,
                    'total_time': stats.total_time,
                    'total_tokens': stats.total_tokens
                }
            }
            
        except Exception as e:
            # 计算耗时
            elapsed_time = time.time() - start_time
            
            # 更新统计信息
            stats = self.stats[model_id]
            stats.total_calls += 1
            stats.failed_calls += 1
            stats.total_time += elapsed_time
            
            return {
                'success': False,
                'error': str(e),
                'model': model_config.model_name,
                'elapsed_time': elapsed_time,
                'stats': {
                    'total_calls': stats.total_calls,
                    'success_calls': stats.success_calls,
                    'failed_calls': stats.failed_calls,
                    'total_time': stats.total_time,
                    'total_tokens': stats.total_tokens
                }
            }
    
    def get_stats(self, model_id: str = None) -> Dict[str, Any]:
        """获取统计信息"""
        if model_id:
            return {model_id: self.stats.get(model_id, CallStats())}
        return dict(self.stats)
    
    def test_model(self, model_id: str, timeout: float = 5.0) -> Dict[str, Any]:
        """测试模型是否可用（探活功能）"""
        model_config = self.get_model_config(model_id)
        if not model_config:
            return {
                'success': False,
                'error': f'模型 {model_id} 不存在或未启用',
                'model': model_id
            }

        client = self.create_client(model_id)
        if not client:
            return {
                'success': False,
                'error': f'无法创建模型 {model_id} 的客户端',
                'model': model_id
            }

        # 简单的测试消息
        test_messages = [
            {"role": "user", "content": "Hello"}
        ]

        # 准备调用参数 - 探活参数
        call_params = {
            'model': model_config.model_name,
            'messages': test_messages,
            'max_tokens': 2,  # 只生成2个token
            'temperature': 0.1,
        }

        # 记录开始时间
        start_time = time.time()

        try:
            # 设置超时
            import threading
            result = {'response': None, 'error': None}

            def call_with_timeout():
                try:
                    response = client.chat.completions.create(**call_params)
                    result['response'] = response
                except Exception as e:
                    result['error'] = e

            thread = threading.Thread(target=call_with_timeout)
            thread.start()
            thread.join(timeout=timeout)

            # 计算耗时
            elapsed_time = time.time() - start_time

            if thread.is_alive():
                # 超时
                return {
                    'success': False,
                    'error': f'模型 {model_id} 响应超时 ({timeout}秒)',
                    'model': model_config.model_name,
                    'elapsed_time': elapsed_time,
                    'timeout': timeout
                }

            if result['error']:
                # 调用出错
                return {
                    'success': False,
                    'error': str(result['error']),
                    'model': model_config.model_name,
                    'elapsed_time': elapsed_time
                }

            # 成功
            response = result['response']
            content = response.choices[0].message.content if response.choices else ""

            return {
                'success': True,
                'content': content,
                'model': model_config.model_name,
                'elapsed_time': elapsed_time,
                'tokens_used': getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') and response.usage else 0
            }

        except Exception as e:
            elapsed_time = time.time() - start_time
            return {
                'success': False,
                'error': str(e),
                'model': model_config.model_name,
                'elapsed_time': elapsed_time
            }

    def reset_stats(self, model_id: str = None):
        """重置统计信息"""
        if model_id:
            if model_id in self.stats:
                self.stats[model_id] = CallStats()
        else:
            for model_id in self.stats:
                self.stats[model_id] = CallStats()
    
    def get_default_model(self) -> str:
        """获取默认模型"""
        return self.defaults.get('model', 'gpt-4o')
    
    def get_default_scenario(self) -> str:
        """获取默认场景"""
        return self.defaults.get('scenario', 'water_engineering')
    
    def get_directory(self, dir_type: str) -> str:
        """获取目录路径"""
        return self.directories.get(dir_type, f"./{dir_type}")
    
    def ensure_directories(self):
        """确保所有目录存在"""
        for dir_type, dir_path in self.directories.items():
            os.makedirs(dir_path, exist_ok=True)

# 全局模型管理器实例
model_manager = ModelManager()

def get_model_manager() -> ModelManager:
    """获取模型管理器实例"""
    return model_manager
