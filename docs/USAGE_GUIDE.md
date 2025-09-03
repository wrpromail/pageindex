# PageIndex 使用指南

## 🎯 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 启动Web界面
streamlit run streamlit_app.py
```

### 2. 配置模型

在 `model_configs.yaml` 中配置你的模型：

```yaml
models:
  your-model:
    name: "Your Model Name"
    api_key: "your-api-key"
    base_url: "https://your-endpoint.com/v1"
    enabled: true
    max_tokens: 4000
    timeout: 30
```

### 3. 准备OCR文件

将OCR工具识别的JSON文件放入 `ocr_files/` 目录。文件格式示例：

```json
[
  {
    "page_idx": 1,
    "type": "text",
    "text": "第一章 工程概况\n本工程位于...",
    "text_level": 1
  },
  {
    "page_idx": 2,
    "type": "table",
    "table_body": "<table><tr><td>项目</td><td>数值</td></tr></table>",
    "table_level": 1
  }
]
```

## 🔧 使用流程

### 步骤1：生成索引

1. 在Streamlit界面选择模型
2. 选择OCR JSON文件
3. 点击"创建索引"
4. 等待索引生成完成

### 步骤2：智能搜索

1. 在搜索页面选择索引文件
2. 输入查询问题
3. 点击"开始搜索"
4. 查看搜索结果和统计信息

## 📊 功能说明

### 索引生成

- **细粒度分析**：每个节点包含1-3页内容
- **表格识别**：自动识别和标记表格
- **关键指标**：提取库容、装机容量等关键数据
- **节点类型**：分类为概述、技术规格、运行数据等

### 智能搜索

- **三步流程**：
  1. 查询分析：理解用户意图
  2. 章节检索：找到相关章节
  3. 答案生成：基于原文生成答案

- **支持查询类型**：
  - 具体数值查询（如"总库容是多少"）
  - 表格数据查询（如"运行数据表格"）
  - 专业术语查询（如"NHQ曲线"）

## 🎨 最佳实践

### 1. 模型选择

- **Qwen3-32B**：适合复杂推理和中文理解
- **GPT-OSS**：适合英文文档和通用查询
- **本地模型**：适合数据安全和隐私要求

### 2. 查询技巧

- **具体明确**：使用具体的数值和术语
- **上下文完整**：提供足够的上下文信息
- **分步查询**：复杂问题可以分步查询

### 3. 性能优化

- **批量处理**：一次处理多个文档
- **模型缓存**：重复使用已生成的索引
- **错误重试**：网络问题时自动重试

## 🔍 故障排除

### 常见问题

1. **索引生成失败**
   - 检查OCR文件格式是否正确
   - 确认模型配置和网络连接
   - 查看错误日志获取详细信息

2. **搜索无结果**
   - 确认索引文件已正确生成
   - 检查查询问题是否明确
   - 尝试不同的查询表达方式

3. **模型调用失败**
   - 验证API密钥和端点配置
   - 检查网络连接和防火墙设置
   - 确认模型服务是否正常

### 调试技巧

1. **查看统计信息**：关注模型调用次数和token使用
2. **检查日志**：查看详细的错误信息和处理流程
3. **测试连接**：使用简单的查询测试模型连接

## 📈 性能监控

### 关键指标

- **索引生成时间**：通常2-3页/分钟
- **搜索响应时间**：通常3-5秒
- **模型调用次数**：每次搜索约3-5次调用
- **Token使用量**：根据文档大小和查询复杂度

### 优化建议

- **合理设置max_tokens**：根据模型能力调整
- **控制并发数**：避免API速率限制
- **缓存索引**：重复使用已生成的索引
- **批量处理**：提高处理效率

## 🚀 高级用法

### 自定义提示词

在 `prompt_config.yaml` 中自定义提示词：

```yaml
scenarios:
  water_engineering:
    structure_analysis: |
      你的自定义结构分析提示词...
    search_analysis: |
      你的自定义搜索分析提示词...
```

### 扩展新场景

1. 在 `prompt_config.yaml` 中添加新场景
2. 在 `model_configs.yaml` 中配置场景参数
3. 测试新场景的提示词效果

### 集成外部系统

```python
from ocr_indexing import generate_ocr_index
from intelligent_ocr_search import search_with_llm

# 生成索引
result = generate_ocr_index("ocr_file.json", "model_id")

# 执行搜索
search_result = search_with_llm("index_file.json", "查询问题", "model_id")
```

---

*更多详细信息请参考项目根目录的 README.md*
