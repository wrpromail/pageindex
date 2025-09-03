# PageIndex API 参考

## 📋 核心模块

### 1. OCR索引生成 (`ocr_indexing.py`)

#### `generate_ocr_index(ocr_file_path, model_id, scenario="water_engineering")`

生成OCR文档的智能索引。

**参数：**
- `ocr_file_path` (str): OCR JSON文件路径
- `model_id` (str): 模型ID
- `scenario` (str): 场景名称，默认"water_engineering"

**返回值：**
```python
{
    "success": True,
    "output_file": "path/to/index.json",
    "indexing_stats": {
        "total_calls": 10,
        "successful_calls": 9,
        "failed_calls": 1,
        "total_time": 120.5,
        "total_tokens": 15000
    }
}
```

**示例：**
```python
from ocr_indexing import generate_ocr_index

result = generate_ocr_index("ddh.pdf_content_list.json", "qwen3-32b")
print(f"索引文件: {result['output_file']}")
```

#### `create_ocr_structure_with_llm(ocr_data, model_config, scenario="water_engineering")`

使用LLM分析OCR数据并生成文档结构。

**参数：**
- `ocr_data` (list): OCR数据列表
- `model_config` (ModelConfig): 模型配置对象
- `scenario` (str): 场景名称

**返回值：**
```python
{
    "structure": [
        {
            "title": "节点标题",
            "start_page": 1,
            "end_page": 3,
            "summary": "节点摘要",
            "has_tables": True,
            "table_count": 2,
            "key_metrics": ["库容", "装机容量"],
            "content_type": "technical_specs",
            "granularity": "high"
        }
    ]
}
```

### 2. 智能搜索 (`intelligent_ocr_search.py`)

#### `search_with_llm(index_file_path, query, model_id, scenario="water_engineering")`

执行智能搜索。

**参数：**
- `index_file_path` (str): 索引文件路径
- `query` (str): 查询问题
- `model_id` (str): 模型ID
- `scenario` (str): 场景名称

**返回值：**
```python
{
    "success": True,
    "answer": "基于文档的详细回答",
    "relevant_chapters": [
        {
            "chapter_id": "chapter_1",
            "relevance_score": 0.9,
            "reason": "包含相关数据"
        }
    ],
    "token_stats": {
        "total_calls": 3,
        "total_tokens": 5000,
        "input_tokens": 3000,
        "output_tokens": 2000
    },
    "call_details": [
        {
            "step": "查询分析",
            "elapsed_time": 2.1,
            "input_tokens": 1000,
            "output_tokens": 500
        }
    ]
}
```

**示例：**
```python
from intelligent_ocr_search import search_with_llm

result = search_with_llm("index.json", "总库容是多少", "qwen3-32b")
if result["success"]:
    print(f"答案: {result['answer']}")
```

#### `intelligent_search(index_data, ocr_data, query, model_config, scenario="water_engineering")`

核心搜索逻辑。

**参数：**
- `index_data` (dict): 索引数据
- `ocr_data` (list): OCR数据
- `query` (str): 查询问题
- `model_config` (ModelConfig): 模型配置
- `scenario` (str): 场景名称

**返回值：** 与 `search_with_llm` 相同

### 3. 模型管理 (`model_manager.py`)

#### `ModelManager`

模型管理器类。

**初始化：**
```python
from model_manager import ModelManager

# 使用默认配置
manager = ModelManager()

# 或指定配置文件
manager = ModelManager("custom_config.yaml")
```

**主要方法：**

##### `get_available_models()`

获取可用模型列表。

**返回值：**
```python
[
    {
        "id": "qwen3-32b",
        "name": "Qwen3-32B",
        "enabled": True
    }
]
```

##### `call_model(prompt, model_id=None, max_retries=3)`

调用模型。

**参数：**
- `prompt` (str): 提示词
- `model_id` (str): 模型ID，默认使用默认模型
- `max_retries` (int): 最大重试次数

**返回值：**
```python
{
    "response": "模型响应",
    "usage": {
        "prompt_tokens": 1000,
        "completion_tokens": 500,
        "total_tokens": 1500
    }
}
```

##### `get_directory(dir_type)`

获取目录路径。

**参数：**
- `dir_type` (str): 目录类型 ("ocr_files", "index_files", "temp_files")

**返回值：** 目录路径字符串

##### `get_indexing_config()`

获取索引配置。

**返回值：**
```python
{
    "toc_check_page_num": 10,
    "max_page_num_each_node": 3,
    "if_add_node_id": True,
    "if_add_node_summary": True,
    "if_add_doc_description": True,
    "if_add_node_text": True
}
```

### 4. 提示词管理 (`prompt_templates.py`)

#### `PromptManager`

提示词管理器类。

**初始化：**
```python
from prompt_templates import PromptManager

manager = PromptManager("prompt_config.yaml")
```

**主要方法：**

##### `get_template(scenario, template_type)`

获取提示词模板。

**参数：**
- `scenario` (str): 场景名称
- `template_type` (str): 模板类型 ("structure_analysis", "search_analysis", "answer_generation")

**返回值：** 提示词模板字符串

##### `format_template(scenario, template_type, **kwargs)`

格式化提示词模板。

**参数：**
- `scenario` (str): 场景名称
- `template_type` (str): 模板类型
- `**kwargs`: 模板变量

**返回值：** 格式化后的提示词字符串

**示例：**
```python
from prompt_templates import prompt_manager

template = prompt_manager.format_template(
    "water_engineering",
    "structure_analysis",
    document_sample="文档内容样本..."
)
```

## 🔧 配置参考

### 模型配置 (`model_configs.yaml`)

```yaml
models:
  model_id:
    name: "模型显示名称"
    api_key: "API密钥"
    base_url: "API端点"
    enabled: true
    max_tokens: 4000
    timeout: 30

scenarios:
  scenario_name:
    name: "场景显示名称"
    description: "场景描述"

directories:
  ocr_files: "ocr_files"
  index_files: "index_files"
  temp_files: "temp_files"

indexing:
  toc_check_page_num: 10
  max_page_num_each_node: 3
  if_add_node_id: true
  if_add_node_summary: true
  if_add_doc_description: true
  if_add_node_text: true
```

### 提示词配置 (`prompt_config.yaml`)

```yaml
scenarios:
  scenario_name:
    name: "场景名称"
    description: "场景描述"
    structure_analysis: |
      结构分析提示词模板...
    search_analysis: |
      搜索分析提示词模板...
    answer_generation: |
      答案生成提示词模板...
```

## 📊 数据结构

### OCR数据格式

```python
[
    {
        "page_idx": 1,           # 页码
        "type": "text",          # 类型: "text" 或 "table"
        "text": "文本内容",      # 文本内容
        "text_level": 1,         # 文本级别
        "table_body": "<table>...</table>",  # 表格HTML（仅table类型）
        "table_level": 1         # 表格级别（仅table类型）
    }
]
```

### 索引数据格式

```python
{
    "doc_name": "文档名称",
    "total_pages": 208,
    "model_id": "qwen3-32b",
    "model_name": "Qwen3-32B",
    "scenario": "water_engineering",
    "created_at": "2024-12-01T10:00:00",
    "structure": [
        {
            "title": "节点标题",
            "start_page": 1,
            "end_page": 3,
            "summary": "节点摘要",
            "has_tables": True,
            "table_count": 2,
            "key_metrics": ["库容", "装机容量"],
            "content_type": "technical_specs",
            "granularity": "high"
        }
    ]
}
```

## 🚀 使用示例

### 完整工作流程

```python
from ocr_indexing import generate_ocr_index
from intelligent_ocr_search import search_with_llm
from model_manager import ModelManager

# 1. 生成索引
index_result = generate_ocr_index("document.json", "qwen3-32b")
if index_result["success"]:
    print(f"索引生成成功: {index_result['output_file']}")
    
    # 2. 执行搜索
    search_result = search_with_llm(
        index_result["output_file"],
        "总库容是多少立方米",
        "qwen3-32b"
    )
    
    if search_result["success"]:
        print(f"搜索结果: {search_result['answer']}")
        print(f"Token使用: {search_result['token_stats']['total_tokens']}")
    else:
        print("搜索失败")
else:
    print("索引生成失败")
```

### 批量处理

```python
import os
from ocr_indexing import generate_ocr_index

# 批量处理多个OCR文件
ocr_files = [f for f in os.listdir("ocr_files") if f.endswith(".json")]
model_id = "qwen3-32b"

for ocr_file in ocr_files:
    print(f"处理文件: {ocr_file}")
    result = generate_ocr_index(f"ocr_files/{ocr_file}", model_id)
    if result["success"]:
        print(f"✅ 成功: {result['output_file']}")
    else:
        print(f"❌ 失败: {ocr_file}")
```

---

*更多详细信息请参考各模块的源代码注释*
