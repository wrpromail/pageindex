#!/usr/bin/env python3
"""
基于OCR JSON文件的PageIndex索引生成
使用高质量的OCR识别结果进行文档结构分析
支持多模型配置和统计信息
"""

import os
import json
import time
import argparse
from pathlib import Path
import openai
from prompt_templates import prompt_manager
from model_manager import get_model_manager
import re

def get_model_config(model_id: str = None):
    """获取模型配置"""
    manager = get_model_manager()
    if model_id:
        model_config = manager.get_model_config(model_id)
        if model_config:
            return {
                'api_key': model_config.api_key,
                'base_url': model_config.base_url,
                'model_name': model_config.model_name,
                'max_tokens': model_config.max_tokens,
                'context_limit': model_config.context_limit
            }
    
    # 如果没有找到模型配置，抛出错误
    raise ValueError(f"模型 {model_id} 不存在或未启用")

def parse_ocr_json(ocr_file: str):
    """解析OCR JSON文件"""
    with open(ocr_file, 'r', encoding='utf-8') as f:
        content_list = json.load(f)
    
    # 按页面组织内容
    pages = {}
    for item in content_list:
        page_idx = item.get('page_idx', 0)
        if page_idx not in pages:
            pages[page_idx] = {'texts': [], 'tables': []}
        
        if item['type'] == 'text':
            pages[page_idx]['texts'].append({
                'text': item['text'],
                'text_level': item.get('text_level', 0)
            })
        elif item['type'] == 'table':
            # 解析HTML表格
            table_html = item['table_body']
            table_data = parse_html_table(table_html)
            pages[page_idx]['tables'].append({
                'caption': item.get('table_caption', []),
                'footnote': item.get('table_footnote', []),
                'data': table_data,
                'img_path': item.get('img_path', '')
            })
    
    return pages

def parse_html_table(html_content: str):
    """解析HTML表格内容"""
    try:
        # 简单的HTML表格解析，提取td和th标签内容
        rows = []
        
        # 使用正则表达式提取表格行
        tr_pattern = r'<tr[^>]*>(.*?)</tr>'
        tr_matches = re.findall(tr_pattern, html_content, re.DOTALL)
        
        for tr_content in tr_matches:
            row = []
            # 提取td和th标签内容
            cell_pattern = r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>'
            cell_matches = re.findall(cell_pattern, tr_content, re.DOTALL)
            
            for cell_content in cell_matches:
                # 清理HTML标签
                clean_text = re.sub(r'<[^>]+>', '', cell_content).strip()
                row.append({
                    'text': clean_text,
                    'rowspan': 1,
                    'colspan': 1
                })
            
            if row:
                rows.append(row)
        
        return rows
    except Exception as e:
        print(f"⚠️ 表格解析失败: {e}")
        return []

def extract_table_summary(table_data):
    """提取表格摘要信息"""
    if not table_data:
        return "无表格数据"
    
    # 提取表头
    headers = []
    if table_data:
        for cell in table_data[0]:
            headers.append(cell['text'])
    
    # 提取关键数据
    key_data = []
    for row in table_data[1:6]:  # 只取前5行数据
        row_data = []
        for cell in row:
            row_data.append(cell['text'])
        key_data.append(' | '.join(row_data))
    
    summary = f"表头: {' | '.join(headers)}\n"
    if key_data:
        summary += f"数据示例: {'; '.join(key_data[:3])}"
    
    return summary

def create_ocr_structure_with_llm(pages, model_id, scenario="water_engineering"):
    """使用LLM分析OCR内容创建文档结构"""
    
    total_pages = len(pages)
    all_structures = []
    
    # 获取模型配置
    manager = get_model_manager()
    model_config = manager.get_model_config(model_id)
    if not model_config:
        raise ValueError(f"模型 {model_id} 不存在或未启用")
    
    context_limit = model_config.context_limit
    max_tokens = model_config.max_tokens
    
    # 估算每页内容长度，动态调整批次大小
    estimated_chars_per_page = 500  # 每页大约500字符
    batch_size = max(10, min(50, context_limit // (estimated_chars_per_page * 2)))  # 保守估计
    
    print(f"🔧 模型配置: {model_config.name} ({model_config.model_name})")
    print(f"📏 上下文限制: {context_limit} tokens")
    print(f"📤 最大输出: {max_tokens} tokens")
    print(f"📦 批次大小: {batch_size} 页/批次")
    print(f"🔄 预计批次: {(total_pages + batch_size - 1) // batch_size} 个")
    
    for batch_start in range(0, total_pages, batch_size):
        batch_end = min(batch_start + batch_size, total_pages)
        print(f"🔄 处理第 {batch_start+1}-{batch_end} 页...")
        
        # 构建当前批次的样本内容
        sample_content = ""
        max_content_length = int(context_limit * 0.6)  # 使用60%的上下文限制
        
        for i in range(batch_start, batch_end):
            if i not in pages:
                continue
                
            page_content = pages[i]
            page_header = f"=== 第{i+1}页 ===\n"
            
            # 检查是否超出长度限制
            if len(sample_content) + len(page_header) > max_content_length:
                print(f"⚠️ 内容长度限制，截断到第{i}页")
                break
                
            sample_content += page_header
            
            # 添加文本内容（动态限制）
            text_count = 0
            max_texts_per_page = max(2, min(5, (max_content_length - len(sample_content)) // 200))
            
            for text_item in page_content['texts']:
                if text_count >= max_texts_per_page:
                    break
                level = text_item.get('text_level', 0)
                # 动态调整文本长度
                max_text_length = max(100, (max_content_length - len(sample_content)) // max_texts_per_page)
                text = text_item['text'][:max_text_length]
                if level > 0:
                    sample_content += f"[标题{level}] {text}\n"
                else:
                    sample_content += f"{text}\n"
                text_count += 1
            
            # 添加表格内容（动态限制）
            table_count = 0
            max_tables_per_page = max(1, min(3, (max_content_length - len(sample_content)) // 300))
            
            for table_item in page_content['tables']:
                if table_count >= max_tables_per_page:
                    break
                table_summary = extract_table_summary(table_item['data'])
                # 限制表格摘要长度
                if len(table_summary) > 200:
                    table_summary = table_summary[:200] + "..."
                sample_content += f"[表格] {table_summary}\n"
                table_count += 1
            
            sample_content += "\n"
        
        # 使用提示词模板
        prompt = prompt_manager.format_template(
            scenario,
            "structure_analysis",
            document_sample=sample_content
        )
    
        # 调用LLM分析当前批次
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 使用模型管理器调用LLM
                messages = [{"role": "user", "content": prompt}]
                result = manager.call_model(model_id, messages, max_tokens=max_tokens)
                
                if not result['success']:
                    raise Exception(f"模型调用失败: {result['error']}")
                
                result_text = result['content'].strip()
                print(f"🔍 LLM返回内容: {result_text[:200]}...")
                print(f"⏱️ 调用耗时: {result['elapsed_time']:.2f}秒")
                print(f"🔢 Token使用: {result['tokens_used']}")
                print(f"📊 累计调用: {result['stats']['total_calls']}次")
                
                # 尝试解析JSON
                structure = None
                
                # 首先尝试直接解析
                try:
                    result = json.loads(result_text)
                    structure = result.get('structure', [])
                except json.JSONDecodeError:
                    # 尝试多种清理方式
                    cleaned_text = result_text
                    
                    # 移除markdown代码块标记
                    if "```json" in cleaned_text:
                        cleaned_text = cleaned_text.split("```json")[1].split("```")[0]
                    elif "```" in cleaned_text:
                        cleaned_text = cleaned_text.split("```")[1].split("```")[0]
                    
                    # 移除可能的额外文本
                    if "{" in cleaned_text and "}" in cleaned_text:
                        start = cleaned_text.find("{")
                        end = cleaned_text.rfind("}") + 1
                        cleaned_text = cleaned_text[start:end]
                    
                    try:
                        result = json.loads(cleaned_text.strip())
                        structure = result.get('structure', [])
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON解析失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                        print(f"原始返回前200字符: {result_text[:200]}")
                        print(f"清理后前200字符: {cleaned_text[:200]}")
                        
                        if attempt < max_retries - 1:
                            print("🔄 重试中...")
                            continue
                        else:
                            print("❌ 多次尝试后仍无法解析JSON，跳过此批次")
                            break
                
                if structure:
                    print(f"✅ 批次 {batch_start+1}-{batch_end} 识别出 {len(structure)} 个节点")
                    all_structures.extend(structure)
                    break
                else:
                    print("⚠️ LLM返回空结构，重试...")
                    continue
                    
            except Exception as e:
                print(f"❌ LLM调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("🔄 重试中...")
                    continue
                else:
                    print("❌ 批次处理失败，跳过此批次")
                    break
    
    print(f"✅ 总共识别出 {len(all_structures)} 个节点")
    return all_structures

def generate_ocr_index(ocr_file: str, scenario: str = "water_engineering", model_id: str = None):
    """基于OCR文件生成索引"""
    
    # 获取模型配置
    manager = get_model_manager()
    if model_id:
        model_config = manager.get_model_config(model_id)
        if not model_config:
            print(f"❌ 模型 {model_id} 不存在或未启用")
            return None
    else:
        model_id = manager.get_default_model()
        model_config = manager.get_model_config(model_id)
    
    print(f"🔧 使用模型: {model_config.name} ({model_config.model_name})")
    print(f"📄 处理OCR文件: {ocr_file}")
    print(f"🎯 场景: {prompt_manager.templates['scenarios'][scenario]['name']}")
    
    try:
        # 解析OCR文件
        print("🔄 解析OCR文件...")
        pages = parse_ocr_json(ocr_file)
        print(f"📄 解析到 {len(pages)} 页")
        
        # 统计表格数量
        total_tables = sum(len(page['tables']) for page in pages.values())
        print(f"📊 发现 {total_tables} 个表格")
        
        # 使用LLM创建结构
        print("🔄 使用LLM分析文档结构...")
        structure = create_ocr_structure_with_llm(pages, model_id, scenario)
        
        # 为每个节点添加ID和页面范围
        for i, node in enumerate(structure):
            node['node_id'] = f"{i:04d}"
            node['start_index'] = node.get('start_page', 1)
            node['end_index'] = node.get('end_page', 1)
        
        # 生成结果
        stats = manager.get_stats(model_id)
        model_stats = stats.get(model_id)
        
        # 将CallStats对象转换为字典
        stats_dict = {}
        if model_stats:
            stats_dict = {
                'total_calls': model_stats.total_calls,
                'success_calls': model_stats.success_calls,
                'failed_calls': model_stats.failed_calls,
                'total_time': model_stats.total_time,
                'total_tokens': model_stats.total_tokens
            }
        
        result = {
            'doc_name': Path(ocr_file).stem,
            'scenario': scenario,
            'model_id': model_id,
            'model_name': model_config.name,
            'total_pages': len(pages),
            'total_tables': total_tables,
            'structure': structure,
            'indexing_stats': stats_dict  # 重命名为indexing_stats，用于Streamlit显示
        }
        
        # 保存结果（不包含统计信息）
        manager.ensure_directories()
        index_dir = manager.get_directory("index_files")
        file_name = Path(ocr_file).stem
        output_file = os.path.join(index_dir, f"{file_name}_{scenario}_{model_id}_ocr_index.json")
        
        # 创建不包含统计信息的索引文件
        index_data = {
            'doc_name': result['doc_name'],
            'scenario': result['scenario'],
            'model_id': result['model_id'],
            'model_name': result['model_name'],
            'total_pages': result['total_pages'],
            'total_tables': result['total_tables'],
            'structure': result['structure']
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 索引生成完成!")
        print(f"📁 保存位置: {output_file}")
        print(f"📄 文档名称: {result['doc_name']}")
        print(f"🌳 节点数: {len(result['structure'])}")
        print(f"📊 表格数: {result['total_tables']}")
        
        # 返回结果字典而不是文件路径
        result['output_file'] = output_file
        return result
        
    except Exception as e:
        print(f"❌ 索引生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """主函数"""
    import os
    
    parser = argparse.ArgumentParser(description='基于OCR的PageIndex索引生成')
    parser.add_argument('--ocr_file', type=str, required=True, help='OCR JSON文件路径')
    parser.add_argument('--scenario', type=str, default='water_engineering', 
                       help='场景类型 (water_engineering, financial_report, technical_manual)')
    parser.add_argument('--model_id', type=str, help='模型ID (从model_configs.yaml中选择)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.ocr_file):
        print(f"❌ OCR文件不存在: {args.ocr_file}")
        return
    
    # 获取模型ID
    manager = get_model_manager()
    if args.model_id:
        if args.model_id not in manager.models:
            print(f"❌ 模型 {args.model_id} 不存在或未启用")
            print(f"可用模型: {list(manager.models.keys())}")
            return
        model_id = args.model_id
    else:
        model_id = manager.get_default_model()
        print(f"🔧 使用默认模型: {model_id}")
    
    generate_ocr_index(args.ocr_file, args.scenario, model_id)

if __name__ == "__main__":
    main()
