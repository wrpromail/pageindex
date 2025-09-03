# PageIndex OCR 智能文档检索系统

## 🚀 快速开始

### 1. 配置模型
编辑 `model_configs.yaml` 文件，设置您的API密钥：

```yaml
models:
  gpt-4o:
    name: "GPT-4o"
    api_key: "your_openai_api_key_here"  # 直接设置API密钥
    base_url: "https://api.openai.com/v1"
    model_name: "gpt-4o"
    max_tokens: 4000
    context_limit: 128000
    enabled: true
```

### 2. 准备OCR文件
将OCR识别的JSON文件放入 `ocr_files/` 目录

### 3. 生成索引
```bash
python ocr_indexing.py --ocr_file ocr_files/your_file.json --model_id gpt-oss
```

### 4. 智能搜索
```bash
python intelligent_ocr_search.py --index_file results/your_file_water_engineering_gpt-oss_ocr_index.json --ocr_file ocr_files/your_file.json --query "您的问题" --model_id gpt-oss
```

### 5. Streamlit Web界面
```bash
streamlit run streamlit_app.py
```

## 📁 目录结构

```
PageIndex/
├── model_configs.yaml          # 统一配置文件
├── ocr_indexing.py            # 索引生成器
├── intelligent_ocr_search.py  # 智能搜索系统
├── streamlit_app.py           # Streamlit Web界面
├── model_manager.py           # 模型管理器
├── prompt_templates.py        # 提示词模板
├── ocr_files/                 # OCR文件目录
├── results/                   # 索引文件目录
└── temp/                      # 临时文件目录
```

## 🔧 配置说明

所有配置都在 `model_configs.yaml` 文件中：

- **models**: 模型配置
- **scenarios**: 场景配置  
- **directories**: 目录配置
- **defaults**: 默认配置

## 🎯 示例查询

- "瀑布沟水电站的总库容是多少立方米？"
- "猴子岩水电站的装机容量和年发电量是多少？"
- "深溪沟水电站的设计洪水位是多少？"