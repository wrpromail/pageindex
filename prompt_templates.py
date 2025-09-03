#!/usr/bin/env python3
"""
提示词模板管理系统
支持不同场景和行业的提示词配置
"""

import json
import os
import yaml
from typing import Dict, List, Optional

class PromptManager:
    def __init__(self, config_file: str = "prompt_config.yaml"):
        self.config_file = config_file
        self.templates = self.load_templates()
    
    def load_templates(self) -> Dict:
        """加载提示词模板"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    return yaml.safe_load(f)
                else:
                    return json.load(f)
        else:
            # 创建默认模板
            default_templates = self.create_default_templates()
            self.save_templates(default_templates)
            return default_templates
    
    def create_default_templates(self) -> Dict:
        """创建默认提示词模板"""
        return {
            "scenarios": {
                "water_engineering": {
                    "name": "水利工程",
                    "description": "适用于水利工程、水电站、水库等文档",
                    "structure_analysis": """
请深入分析以下水利工程文档内容，创建细粒度的文档结构索引。这是一个包含大量技术参数、表格和图表的水利工程文档。

文档内容样本：
{document_sample}

请返回以下格式的JSON：
```json
{{
    "structure": [
        {{
            "title": "节点标题",
            "start_page": "开始页码",
            "end_page": "结束页码",
            "summary": "节点摘要",
            "has_tables": "true/false",
            "table_count": "表格数量估计",
            "key_metrics": ["关键指标1", "关键指标2"],
            "content_type": "节点类型",
            "granularity": "细粒度级别"
        }}
    ]
}}
```

要求：
1. 创建超细粒度索引，每个节点包含1-3页内容，不要超过3页
2. 识别所有有意义的内容单元：
   - 工程概况和基本信息
   - 技术参数表格（每个重要表格单独成节点）
   - 运行数据表格（每个重要表格单独成节点）
   - 经济分析数据
   - 环境影响评估
   - 操作流程说明
   - 故障排除指南
   - 附录和参考资料
3. 特别关注表格密集的页面，每个重要表格应该单独成节点
4. 识别关键指标：库容、装机容量、发电量、水位、流量、投资、收益等
5. 标注节点类型：overview(概述)、technical_specs(技术规格)、operational_data(运行数据)、economic_analysis(经济分析)、tables(表格数据)、procedures(操作流程)等
6. 细粒度级别：high(高-单页或单表)、medium(中-2-3页)、low(低-3页)
7. 对于208页包含213个表格的文档，应该创建80-150个超细粒度节点
8. 每个水电站的概况、工程特性、工作表应该分别成节点
9. 重要表格（如库容-水位关系、流量曲线、NHQ曲线等）应该单独成节点
10. 必须返回有效的JSON格式，不要包含任何其他文字
""",
                    "search_analysis": """
请分析以下查询问题，找到最相关的文档章节。

查询问题：{query}

可用章节：
{available_chapters}

请直接返回以下格式的JSON，不要包含任何其他内容或标签：
{{
    "query_analysis": "查询意图分析",
    "search_strategy": "搜索策略说明",
    "relevant_chapters": [
        {{
            "chapter_id": "章节ID",
            "relevance_score": 0.9,
            "reason": "选择理由",
            "expected_info": "期望找到的信息"
        }}
    ]
}}

重要：请只返回JSON格式，不要包含<think>、```等标签或额外说明。
要求：
1. 分析查询意图，理解用户想要获取什么信息
2. 从可用章节中找到最相关的章节
3. 提供详细的推理过程
4. 为每个相关章节打分（0-1）
5. 必须返回有效的JSON格式
""",
                    "answer_generation": """
请基于以下文档内容回答用户问题。

用户问题：{query}

相关文档内容：
{relevant_content}

请提供准确、详细的回答：
1. 直接回答用户问题
2. 引用具体的数值、数据
3. 如果涉及表格，说明表格位置
4. 如果信息不完整，说明需要查看哪些章节
5. 保持专业性和准确性

回答：
"""
                },
                "financial_report": {
                    "name": "财务报告",
                    "description": "适用于上市公司年报、财务报告等文档",
                    "structure_analysis": """
请分析以下财务报告文档，识别出详细的章节结构。

文档内容样本：
{document_sample}

请返回以下格式的JSON：
{{
    "structure": [
        {{
            "title": "章节标题",
            "start_page": 开始页码,
            "end_page": 结束页码,
            "summary": "章节摘要",
            "has_tables": true/false,
            "table_count": 表格数量估计,
            "key_metrics": ["关键财务指标1", "关键财务指标2"]
        }}
    ]
}}

要求：
1. 识别出所有主要章节，包括公司概况、财务数据、业务分析、风险因素等
2. 特别关注包含财务表格的章节
3. 识别关键财务指标（如营收、利润、资产负债等）
4. 必须返回有效的JSON格式
""",
                    "search_analysis": """
请分析以下财务查询问题，找到最相关的报告章节。

查询问题：{query}

可用章节：
{available_chapters}

请返回相关章节的JSON格式分析。
""",
                    "answer_generation": """
请基于以下财务报告内容回答用户问题。

用户问题：{query}

相关文档内容：
{relevant_content}

请提供准确的财务数据回答。
"""
                },
                "technical_manual": {
                    "name": "技术手册",
                    "description": "适用于技术文档、操作手册、产品说明书等",
                    "structure_analysis": """
请分析以下技术手册文档，识别出详细的章节结构。

文档内容样本：
{document_sample}

请返回以下格式的JSON：
{{
    "structure": [
        {{
            "title": "章节标题",
            "start_page": 开始页码,
            "end_page": 结束页码,
            "summary": "章节摘要",
            "has_tables": true/false,
            "table_count": 表格数量估计,
            "key_metrics": ["关键技术参数1", "关键技术参数2"]
        }}
    ]
}}

要求：
1. 识别出所有主要章节，包括概述、技术规格、操作流程、故障排除等
2. 特别关注包含技术参数表格的章节
3. 识别关键技术参数
4. 必须返回有效的JSON格式
""",
                    "search_analysis": """
请分析以下技术查询问题，找到最相关的手册章节。

查询问题：{query}

可用章节：
{available_chapters}

请返回相关章节的JSON格式分析。
""",
                    "answer_generation": """
请基于以下技术手册内容回答用户问题。

用户问题：{query}

相关文档内容：
{relevant_content}

请提供准确的技术回答。
"""
                }
            }
        }
    
    def save_templates(self, templates: Dict):
        """保存提示词模板"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                yaml.dump(templates, f, default_flow_style=False, allow_unicode=True, indent=2)
            else:
                json.dump(templates, f, indent=2, ensure_ascii=False)
    
    def get_template(self, scenario: str, template_type: str) -> str:
        """获取指定场景的提示词模板"""
        if scenario not in self.templates["scenarios"]:
            raise ValueError(f"未知场景: {scenario}")
        
        if template_type not in self.templates["scenarios"][scenario]:
            raise ValueError(f"未知模板类型: {template_type}")
        
        return self.templates["scenarios"][scenario][template_type]
    
    def format_template(self, scenario: str, template_type: str, **kwargs) -> str:
        """格式化提示词模板"""
        template = self.get_template(scenario, template_type)

        # 安全地格式化模板，只替换已知的安全占位符
        formatted_template = template
        for key, value in kwargs.items():
            # 使用更安全的方式替换占位符，避免误匹配JSON模板中的内容
            placeholder = "{" + key + "}"
            if placeholder in formatted_template:
                formatted_template = formatted_template.replace(placeholder, str(value))

        return formatted_template
    
    def list_scenarios(self) -> List[Dict]:
        """列出所有可用场景"""
        scenarios = []
        for key, value in self.templates["scenarios"].items():
            scenarios.append({
                "key": key,
                "name": value["name"],
                "description": value["description"]
            })
        return scenarios
    
    def add_scenario(self, key: str, name: str, description: str, templates: Dict):
        """添加新场景"""
        self.templates["scenarios"][key] = {
            "name": name,
            "description": description,
            **templates
        }
        self.save_templates(self.templates)
    
    def update_template(self, scenario: str, template_type: str, new_template: str):
        """更新提示词模板"""
        if scenario not in self.templates["scenarios"]:
            raise ValueError(f"未知场景: {scenario}")
        
        self.templates["scenarios"][scenario][template_type] = new_template
        self.save_templates(self.templates)

# 全局提示词管理器实例
prompt_manager = PromptManager()

if __name__ == "__main__":
    # 测试提示词管理器
    pm = PromptManager()
    
    print("可用场景:")
    for scenario in pm.list_scenarios():
        print(f"- {scenario['key']}: {scenario['name']} - {scenario['description']}")
    
    # 测试获取模板
    template = pm.format_template(
        "water_engineering", 
        "structure_analysis",
        document_sample="测试文档内容"
    )
    print(f"\n水利工程结构分析模板:\n{template[:200]}...")
