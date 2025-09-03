# PageIndex 文档

## 📋 项目概述

PageIndex 是一个基于大语言模型的智能文档检索系统，专门用于处理长文档的OCR数据和表格内容。系统使用LLM进行文档结构分析和智能搜索，支持水利工程等专业领域。

## 🏗️ 系统架构

### 核心组件

1. **OCR索引生成** (`ocr_indexing.py`)
   - 处理OCR JSON文件
   - 使用LLM进行细粒度文档结构分析
   - 生成包含表格和关键指标的索引

2. **智能搜索** (`intelligent_ocr_search.py`)
   - 三步式LLM搜索流程
   - 查询分析 → 章节检索 → 答案生成
   - 支持复杂查询和表格数据检索

3. **模型管理** (`model_manager.py`)
   - 统一管理多个LLM模型配置
   - 支持OpenAI兼容的API
   - 统计模型调用和token使用

4. **提示词管理** (`prompt_templates.py`)
   - 基于YAML的提示词配置
   - 支持不同场景的提示词模板
   - 水利工程专业提示词

5. **Web界面** (`streamlit_app.py`)
   - 模型选择和配置
   - OCR文件上传和索引生成
   - 智能搜索测试界面

## 🚀 快速开始

### 1. 环境配置

```bash
# 安装依赖
pip install -r requirements.txt

# 配置模型（在model_configs.yaml中）
models:
  qwen3-32b:
    name: "Qwen3-32B"
    api_key: "your-api-key"
    base_url: "https://your-endpoint.com/v1"
    enabled: true
```

### 2. 准备OCR数据

将OCR工具识别的JSON文件放入`ocr_files/`目录：
```json
[
  {
    "page_idx": 1,
    "type": "text",
    "text": "文档内容...",
    "text_level": 1
  },
  {
    "page_idx": 2,
    "type": "table",
    "table_body": "<table>...</table>",
    "table_level": 1
  }
]
```

### 3. 生成索引

```bash
# 命令行方式
python ocr_indexing.py --ocr_file ddh.pdf_content_list.json --model_id qwen3-32b

# 或使用Web界面
streamlit run streamlit_app.py
```

### 4. 智能搜索

```bash
# 命令行方式
python intelligent_ocr_search.py --index_file ddh_water_engineering_qwen3-32b_ocr_index.json --model_id qwen3-32b

# 或使用Web界面进行交互式搜索
```

## 📊 功能特性

### ✅ 已实现功能

- **OCR数据处理**：支持结构化OCR JSON文件解析
- **细粒度索引**：1-3页/节点，识别表格和关键指标
- **LLM搜索**：三步式智能搜索流程
- **多模型支持**：支持OpenAI兼容的API
- **Web界面**：Streamlit交互式界面
- **Token统计**：详细的模型调用和token使用统计
- **配置管理**：YAML统一配置文件

### 🎯 核心优势

- **专业领域优化**：针对水利工程等专业文档优化
- **表格识别**：专门处理包含大量表格的文档
- **智能检索**：基于LLM的语义理解和检索
- **细粒度分析**：超细粒度的文档结构分析
- **易于扩展**：支持新模型和场景的快速集成

## 📁 目录结构

```
PageIndex/
├── docs/                    # 文档目录
├── ocr_files/              # OCR输入文件
├── index_files/            # 生成的索引文件
├── model_configs.yaml      # 统一配置文件
├── prompt_config.yaml      # 提示词配置
├── ocr_indexing.py         # OCR索引生成
├── intelligent_ocr_search.py # 智能搜索
├── model_manager.py        # 模型管理
├── prompt_templates.py     # 提示词管理
├── streamlit_app.py        # Web界面
└── requirements.txt        # 依赖包
```

## 🔧 配置说明

### 模型配置 (`model_configs.yaml`)

```yaml
models:
  qwen3-32b:
    name: "Qwen3-32B"
    api_key: "your-api-key"
    base_url: "https://your-endpoint.com/v1"
    enabled: true
    max_tokens: 4000
    timeout: 30

scenarios:
  water_engineering:
    name: "水利工程"
    description: "适用于水利工程、水电站、水库等文档"

directories:
  ocr_files: "ocr_files"
  index_files: "index_files"
  temp_files: "temp_files"
```

### 提示词配置 (`prompt_config.yaml`)

```yaml
scenarios:
  water_engineering:
    name: "水利工程"
    structure_analysis: |
      请深入分析以下水利工程文档内容...
    search_analysis: |
      请分析以下查询问题...
    answer_generation: |
      请基于以下文档内容回答用户问题...
```

## 📈 性能指标

### 索引生成性能

- **处理速度**：约2-3页/分钟（取决于模型响应速度）
- **索引粒度**：1-3页/节点，包含表格识别
- **准确率**：基于LLM的语义理解，准确率较高

### 搜索性能

- **响应时间**：3-5秒（三步式LLM搜索）
- **搜索精度**：基于语义理解的智能检索
- **支持查询**：复杂查询、表格数据查询、专业术语查询

## 🛠️ 故障排除

### 常见问题

1. **模型调用失败**
   - 检查API密钥和端点配置
   - 确认网络连接正常
   - 查看模型调用统计

2. **索引生成失败**
   - 检查OCR文件格式
   - 确认模型配置正确
   - 查看错误日志

3. **搜索无结果**
   - 确认索引文件存在
   - 检查查询问题格式
   - 查看模型调用详情

## 📞 支持

如有问题，请查看：
- 项目根目录的 `README.md`
- 各模块的代码注释
- Streamlit界面的错误提示

---

*最后更新: 2024年12月*
