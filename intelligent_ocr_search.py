#!/usr/bin/env python3
"""
智能OCR搜索系统
基于PageIndex理念：用户问题 + 索引 → LLM判断 → 定位页码 → 提取原文 → 生成回答
支持多模型配置和统计信息
"""

import os
import json
import time
import argparse

from prompt_templates import prompt_manager
from model_manager import get_model_manager
import re


def load_ocr_index(index_file: str):
    """加载OCR索引文件"""
    with open(index_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_ocr_data(ocr_file: str):
    """加载OCR原始数据"""
    with open(ocr_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_table_text(html_content: str):
    """从HTML表格中提取文本"""
    try:
        # 使用正则表达式提取表格内容
        cell_pattern = r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>'
        cells = re.findall(cell_pattern, html_content, re.DOTALL)

        # 清理HTML标签
        clean_cells = []
        for cell in cells:
            clean_text = re.sub(r'<[^>]+>', '', cell).strip()
            if clean_text:
                clean_cells.append(clean_text)

        return ' | '.join(clean_cells[:15])  # 取更多单元格
    except Exception as e:
        return f"表格解析失败: {e}"


def intelligent_search(query: str, index: dict, ocr_data: list, model_id: str, scenario: str = "water_engineering"):
    """
    智能搜索流程：
    1. 用户问题 + 索引 → LLM判断相关章节
    2. 定位特定页码范围
    3. 提取原文内容
    4. 生成最终回答
    """

    # 获取模型配置
    manager = get_model_manager()
    model_config = manager.get_model_config(model_id)
    if not model_config:
        raise ValueError(f"模型 {model_id} 不存在或未启用")

    # 第一步：LLM分析查询意图，找到最相关的章节
    print("🧠 第一步：分析查询意图，定位相关章节...")

    # 记录模型调用详情
    call_details = []

    # 准备章节信息
    chapters_info = []
    for i, chapter in enumerate(index['structure']):
        chapters_info.append({
            "chapter_id": str(i),
            "title": chapter['title'],
            "summary": chapter['summary'],
            "start_page": chapter['start_page'],
            "end_page": chapter['end_page'],
            "has_tables": chapter.get('has_tables', False),
            "table_count": chapter.get('table_count', 0),
            "key_metrics": chapter.get('key_metrics', [])
        })

    # 使用LLM进行智能分析
    search_prompt = f"""
你是一个专业的文档检索助手。请分析用户查询，找到最相关的文档章节。

用户查询：{query}

可用章节列表：
{json.dumps(chapters_info, ensure_ascii=False, indent=2)}

请直接返回以下格式的JSON，不要包含任何其他内容或标签：
{{
    "query_analysis": "分析用户查询意图，说明要找什么信息",
    "relevant_chapters": [
        {{
            "chapter_id": "章节ID",
            "relevance_score": 0.9,
            "reason": "为什么选择这个章节",
            "expected_info": "期望在这个章节找到什么信息"
        }}
    ],
    "search_strategy": "搜索策略说明"
}}

重要：请只返回JSON格式，不要包含<think>、```等标签或额外说明。

要求：
1. 仔细分析用户查询意图
2. 从可用章节中找到最相关的章节（最多3个）
3. 为每个相关章节打分（0-1）
4. 说明选择理由和期望找到的信息
5. 必须返回有效的JSON格式
"""

    try:
        # 使用模型管理器调用LLM
        messages = [{"role": "user", "content": search_prompt}]
        result = manager.call_model(model_id, messages, max_tokens=min(1000, model_config.max_tokens // 2))

        if not result['success']:
            raise Exception(f"模型调用失败: {result['error']}")

        result_text = result['content'].strip()
        print(f"⏱️ 搜索分析耗时: {result['elapsed_time']:.2f}秒")
        print(
            f"🔢 Token使用: {result['tokens_used']} (输入: {result.get('input_tokens', 0)}, 输出: {result.get('output_tokens', 0)})")

        # 记录第一步调用详情
        call_details.append({
            "step": "第一步：查询分析",
            "elapsed_time": result['elapsed_time'],
            "input_tokens": result.get('input_tokens', 0),
            "output_tokens": result.get('output_tokens', 0),
            "total_tokens": result['tokens_used']
        })

        # 解析LLM返回的搜索分析
        try:
            search_result = json.loads(result_text)
        except json.JSONDecodeError:
            print(f"⚠️ JSON解析失败，尝试清理格式...")

            # 多种清理策略
            cleaned_text = result_text

            # 1. 移除<think>标签及其内容
            if "<think>" in cleaned_text:
                if "</think>" in cleaned_text:
                    # 移除完整的<think>...</think>块
                    cleaned_text = re.sub(r'<think>.*?</think>', '', cleaned_text, flags=re.DOTALL)
                else:
                    # 只有开始标签，移除从<think>开始的所有内容
                    cleaned_text = cleaned_text.split("<think>")[0]

            # 2. 移除markdown代码块
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0]
            elif "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[1].split("```")[0]

            # 3. 查找JSON对象
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if json_match:
                cleaned_text = json_match.group(0)

            # 4. 清理多余的空白字符
            cleaned_text = cleaned_text.strip()

            try:
                search_result = json.loads(cleaned_text)
                print(f"✅ JSON清理成功")
            except json.JSONDecodeError as e2:
                print(f"❌ JSON清理后仍解析失败: {e2}")
                print(f"清理后的内容: {cleaned_text[:500]}...")
                print(f"原始返回内容: {result_text[:500]}...")
                return None

        query_analysis = search_result.get('query_analysis', '')
        relevant_chapters = search_result.get('relevant_chapters', [])
        search_strategy = search_result.get('search_strategy', '')

        print(f"💭 查询分析: {query_analysis}")
        print(f"🎯 搜索策略: {search_strategy}")
        print(f"📋 找到相关章节: {len(relevant_chapters)}个")

    except Exception as e:
        print(f"❌ 搜索分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    if not relevant_chapters:
        return {
            "query": query,
            "answer": "抱歉，未找到相关信息。",
            "relevant_chapters": [],
            "search_time": 0
        }

    # 第二步：提取相关章节的原文内容
    print("📖 第二步：提取相关章节的原文内容...")

    relevant_content = ""
    chapter_details = []

    try:

        for rel_chapter in relevant_chapters[:3]:  # 最多处理3个章节
            chapter_id = int(rel_chapter['chapter_id'])
            if chapter_id >= len(index['structure']):
                continue

            chapter = index['structure'][chapter_id]
            chapter_details.append({
                'title': chapter['title'],
                'start_page': chapter['start_page'],
                'end_page': chapter['end_page'],
                'relevance_score': rel_chapter.get('relevance_score', 0.5),
                'reason': rel_chapter.get('reason', ''),
                'expected_info': rel_chapter.get('expected_info', '')
            })

            # 提取该章节的原文内容
            chapter_content = ""
            for item in ocr_data:
                page_idx = item.get('page_idx', 0)
                if chapter['start_page'] <= page_idx + 1 <= chapter['end_page']:  # 转换为1基索引
                    if item['type'] == 'text':
                        chapter_content += f"{item['text']}\n"
                    elif item['type'] == 'table':
                        table_text = extract_table_text(item['table_body'])
                        chapter_content += f"[表格] {table_text}\n"

            relevant_content += f"=== {chapter['title']} (第{chapter['start_page']}-{chapter['end_page']}页) ===\n"
            relevant_content += f"章节摘要: {chapter['summary']}\n"
            relevant_content += f"选择理由: {rel_chapter.get('reason', '')}\n"
            relevant_content += f"期望信息: {rel_chapter.get('expected_info', '')}\n"
            relevant_content += f"原文内容:\n{chapter_content}\n\n"

    except Exception as e:
        print(f"❌ 第二步失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 第三步：基于原文内容生成最终回答
    print("💡 第三步：基于原文内容生成最终回答...")

    answer_prompt = f"""
你是一个专业的技术文档问答助手。请基于提供的文档内容，准确回答用户问题。

用户问题：{query}

相关文档内容：
{relevant_content}

请提供准确、详细的回答：
1. 直接回答用户问题，提供具体数值和数据
2. 引用文档中的具体内容，说明数据来源
3. 如果涉及表格，说明表格位置和内容
4. 如果信息不完整，说明需要查看哪些其他章节
5. 保持专业性和准确性

回答格式：
**答案**
[直接回答用户问题]

**数据来源**
[说明信息来源的章节和页码]

**详细信息**
[提供更多相关细节]
"""

    try:
        # 调用LLM生成回答
        result = manager.call_model(
            model_id=model_id,
            messages=[{"role": "user", "content": answer_prompt}],
            max_tokens=getattr(model_config, 'max_tokens', 2000),
            temperature=0.1
        )

        if result and result.get('content'):
            answer = result['content'].strip()

            # 清理回答中的<think>标签
            if "<think>" in answer:
                if "</think>" in answer:
                    # 移除完整的<think>...</think>块
                    answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL)
                else:
                    # 只有开始标签，移除从<think>开始的所有内容
                    answer = answer.split("<think>")[0]
                answer = answer.strip()

            print(f"✅ 回答生成成功")
            print(
                f"🔢 Token使用: {result['tokens_used']} (输入: {result.get('input_tokens', 0)}, 输出: {result.get('output_tokens', 0)})")

            # 记录第三步调用详情
            call_details.append({
                "step": "第三步：回答生成",
                "elapsed_time": result['elapsed_time'],
                "input_tokens": result.get('input_tokens', 0),
                "output_tokens": result.get('output_tokens', 0),
                "total_tokens": result['tokens_used']
            })

            return {
                "query": query,
                "answer": answer,
                "relevant_chapters": chapter_details,
                "search_time": 0,
                "token_stats": {
                    "total_tokens": result['tokens_used'],
                    "input_tokens": result.get('input_tokens', 0),
                    "output_tokens": result.get('output_tokens', 0)
                },
                "call_details": call_details
            }
        else:
            print(f"❌ LLM返回空内容")
            return {
                "query": query,
                "answer": "抱歉，无法生成回答。",
                "relevant_chapters": chapter_details,
                "search_time": 0
            }

    except Exception as e:
        print(f"❌ 回答生成失败: {e}")
        return {
            "query": query,
            "answer": f"抱歉，无法生成回答：{e}",
            "relevant_chapters": chapter_details,
            "search_time": 0
        }


def search_with_llm(index_file: str, ocr_file: str, query: str, model_id: str, scenario: str = "water_engineering"):
    """供Gradio使用的搜索函数"""
    try:
        # 加载数据
        index = load_ocr_index(index_file)
        ocr_data = load_ocr_data(ocr_file)

        # 执行搜索
        print(f"🔍 开始执行智能搜索...")
        result = intelligent_search(query, index, ocr_data, model_id, scenario)
        print(f"🔍 智能搜索完成，结果类型: {type(result)}")

        # 检查结果是否为None
        if result is None:
            print(f"❌ 智能搜索返回None")
            return {
                "success": False,
                "error": "搜索分析失败",
                "answer": None,
                "relevant_chapters": [],
                "query": query
            }

        return {
            "success": True,
            "answer": result.get("answer", "无回答"),
            "relevant_chapters": result.get("relevant_chapters", []),
            "query": query,
            "token_stats": result.get("token_stats", {}),
            "call_details": result.get("call_details", [])
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "answer": None,
            "relevant_chapters": [],
            "query": query
        }

    # 第二步：提取相关章节的原文内容
    print("📖 第二步：提取相关章节的原文内容...")

    relevant_content = ""
    chapter_details = []

    try:

        for rel_chapter in relevant_chapters[:3]:  # 最多处理3个章节
            chapter_id = int(rel_chapter['chapter_id'])
            if chapter_id >= len(index['structure']):
                continue

            chapter = index['structure'][chapter_id]
            chapter_details.append({
                'title': chapter['title'],
                'start_page': chapter['start_page'],
                'end_page': chapter['end_page'],
                'relevance_score': rel_chapter.get('relevance_score', 0.5),
                'reason': rel_chapter.get('reason', ''),
                'expected_info': rel_chapter.get('expected_info', '')
            })

            # 提取该章节的原文内容
            chapter_content = ""
            for item in ocr_data:
                page_idx = item.get('page_idx', 0)
                if chapter['start_page'] <= page_idx + 1 <= chapter['end_page']:  # 转换为1基索引
                    if item['type'] == 'text':
                        chapter_content += f"{item['text']}\n"
                    elif item['type'] == 'table':
                        table_text = extract_table_text(item['table_body'])
                        chapter_content += f"[表格] {table_text}\n"

            relevant_content += f"=== {chapter['title']} (第{chapter['start_page']}-{chapter['end_page']}页) ===\n"
            relevant_content += f"章节摘要: {chapter['summary']}\n"
            relevant_content += f"选择理由: {rel_chapter.get('reason', '')}\n"
            relevant_content += f"期望信息: {rel_chapter.get('expected_info', '')}\n"
            relevant_content += f"原文内容:\n{chapter_content}\n\n"

    except Exception as e:
        print(f"❌ 第二步失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 第三步：基于原文内容生成最终回答
    print("💡 第三步：基于原文内容生成最终回答...")

    answer_prompt = f"""
你是一个专业的技术文档问答助手。请基于提供的文档内容，准确回答用户问题。

用户问题：{query}

相关文档内容：
{relevant_content}

请提供准确、详细的回答：
1. 直接回答用户问题，提供具体数值和数据
2. 引用文档中的具体内容，说明数据来源
3. 如果涉及表格，说明表格位置和内容
4. 如果信息不完整，说明需要查看哪些其他章节
5. 保持专业性和准确性

回答格式：
**答案**
[直接回答用户问题]

**数据来源**
[说明数据来源和位置]

**补充说明**
[其他相关信息]
"""

    try:
        # 使用模型管理器调用LLM
        messages = [{"role": "user", "content": answer_prompt}]
        result = manager.call_model(model_id, messages, max_tokens=model_config.max_tokens)

        if not result['success']:
            raise Exception(f"模型调用失败: {result['error']}")

        answer = result['content'].strip()
        print(f"⏱️ 回答生成耗时: {result['elapsed_time']:.2f}秒")
        print(f"🔢 Token使用: {result['tokens_used']}")

        return {
            "query": query,
            "answer": answer,
            "relevant_chapters": chapter_details,
            "search_time": 0  # 将在调用处计算
        }

    except Exception as e:
        print(f"❌ 回答生成失败: {e}")
        return {
            "query": query,
            "answer": f"抱歉，无法生成回答：{e}",
            "relevant_chapters": chapter_details,
            "search_time": 0
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='智能OCR搜索系统')
    parser.add_argument('--index_file', type=str, required=True, help='OCR索引文件路径')
    parser.add_argument('--ocr_file', type=str, required=True, help='OCR原始文件路径')
    parser.add_argument('--scenario', type=str, default='water_engineering',
                        help='场景类型')
    parser.add_argument('--model_id', type=str, help='模型ID (从model_configs.yaml中选择)')
    parser.add_argument('--query', type=str, help='单次查询问题')

    args = parser.parse_args()

    if not os.path.exists(args.index_file):
        print(f"❌ 索引文件不存在: {args.index_file}")
        return

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

    # 加载数据
    print("📚 加载索引和OCR数据...")
    index = load_ocr_index(args.index_file)
    ocr_data = load_ocr_data(args.ocr_file)

    print(f"📄 文档: {index['doc_name']}")
    print(f"🌳 章节数: {len(index['structure'])}")
    print(f"📊 表格数: {index.get('total_tables', 0)}")
    print(f"🎯 场景: {prompt_manager.templates['scenarios'][args.scenario]['name']}")
    print(f"🤖 模型: {model_id}")
    print()

    if args.query:
        # 单次查询
        start_time = time.time()
        result = intelligent_search(args.query, index, ocr_data, model_id, args.scenario)
        result['search_time'] = time.time() - start_time

        print(f"🔍 查询: {result['query']}")
        print(f"⏱️ 搜索时间: {result['search_time']:.4f}秒")

        if result['relevant_chapters']:
            print(f"\n📋 找到 {len(result['relevant_chapters'])} 个相关章节:")
            for i, chapter in enumerate(result['relevant_chapters'], 1):
                print(f"{i}. **{chapter['title']}** (第{chapter['start_page']}-{chapter['end_page']}页)")
                print(f"   相关性: {chapter['reason']}")
                print(f"   期望信息: {chapter['expected_info']}")
                print()

        print(f"\n💡 回答:")
        print(result['answer'])
    else:
        # 交互式搜索
        print("🔍 智能OCR搜索系统")
        print("=" * 60)

        while True:
            query = input("请输入查询问题 (输入 'quit' 退出): ").strip()

            if query.lower() == 'quit':
                print("👋 再见!")
                break

            if not query:
                continue

            print(f"\n🔍 查询: {query}")

            # 执行智能搜索
            start_time = time.time()
            result = intelligent_search(query, index, ocr_data, model_id, args.scenario)
            result['search_time'] = time.time() - start_time

            print(f"⏱️ 搜索时间: {result['search_time']:.4f}秒")

            if result['relevant_chapters']:
                print(f"\n📋 找到 {len(result['relevant_chapters'])} 个相关章节:")
                for i, chapter in enumerate(result['relevant_chapters'], 1):
                    print(f"{i}. **{chapter['title']}** (第{chapter['start_page']}-{chapter['end_page']}页)")
                    print(f"   相关性: {chapter['reason']}")
                    print()

            print(f"\n💡 回答:")
            print(result['answer'])
            print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
