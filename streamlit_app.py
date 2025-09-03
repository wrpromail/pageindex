#!/usr/bin/env python3
"""
PageIndex OCR Streamlit Web UI
支持多模型选择、索引生成和智能搜索测试
"""

import streamlit as st
import os
import json
import time
from pathlib import Path
from model_manager import get_model_manager
from ocr_indexing import generate_ocr_index, parse_ocr_json
from intelligent_ocr_search import search_with_llm
from prompt_templates import prompt_manager

# 页面配置
st.set_page_config(
    page_title="PageIndex OCR 智能文档检索系统",
    page_icon="🚀",
    layout="wide"
)

# 全局变量
def get_manager():
    """获取或创建模型管理器实例"""
    if 'model_manager' not in st.session_state:
        st.session_state.model_manager = get_model_manager()
    return st.session_state.model_manager

# 初始化manager
if 'model_manager' not in st.session_state:
    st.session_state.model_manager = get_model_manager()

manager = get_manager()

def get_available_ocr_files():
    """获取可用的OCR文件列表"""
    ocr_files = []
    ocr_dir = manager.get_directory("ocr_files")
    if os.path.exists(ocr_dir):
        for file in os.listdir(ocr_dir):
            if file.endswith(".json") and "content_list" in file:
                ocr_files.append(os.path.join(ocr_dir, file))
    return ocr_files

def get_available_index_files():
    """获取可用的索引文件列表"""
    index_files = []
    index_dir = manager.get_directory("index_files")
    if os.path.exists(index_dir):
        for file in os.listdir(index_dir):
            if file.endswith("_ocr_index.json"):
                index_files.append(os.path.join(index_dir, file))
    return index_files

def main():
    st.title("🚀 PageIndex OCR 智能文档检索系统")
    st.markdown("支持多模型配置、索引生成和智能搜索测试")
    
    # 侧边栏 - 模型管理
    with st.sidebar:
        st.header("🤖 模型管理")
        
        # 模型选择
        available_models = manager.get_available_models()
        model_options = {f"{model['name']} ({model['id']})": model['id'] 
                        for model in available_models}
        
        selected_model = st.selectbox(
            "选择模型",
            options=list(model_options.keys()),
            index=0
        )
        model_id = model_options[selected_model]
        
        # 模型信息
        model_config = manager.get_model_config(model_id)
        if model_config:
            st.info(f"""
            **模型**: {model_config.name}
            **上下文限制**: {model_config.context_limit:,} tokens
            **最大输出**: {model_config.max_tokens:,} tokens
            """)

            # 配置更新按钮
            if st.button("🔄 更新配置", type="secondary"):
                try:
                    # 重新加载模型管理器的配置
                    st.session_state.model_manager.load_config()
                    st.success("✅ 配置已重新加载！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 配置重新加载失败: {str(e)}")

            # 模型测试按钮
            if st.button("🩺 测试模型", type="secondary"):
                with st.spinner("正在测试模型连接..."):
                    try:
                        test_result = st.session_state.model_manager.test_model(model_id, timeout=5.0)

                        if test_result.get('success'):
                            st.success("✅ 模型连接成功!")
                            st.info(f"""
                            📊 **测试结果**:
                            - 响应时间: {test_result.get('elapsed_time', 0):.2f}秒
                            - Token使用: {test_result.get('tokens_used', 0)}
                            - 模型: {test_result.get('model', '')}
                            """)
                        else:
                            st.error("❌ 模型连接失败!")
                            st.warning(f"""
                            📊 **错误信息**:
                            - 错误: {test_result.get('error', '未知错误')}
                            - 响应时间: {test_result.get('elapsed_time', 0):.2f}秒
                            - 模型: {test_result.get('model', '')}
                            """)

                    except Exception as e:
                        st.error(f"❌ 测试过程中发生异常: {str(e)}")
    
    # 主界面
    tab1, tab2, tab3 = st.tabs(["📚 索引生成", "🔍 搜索测试", "⚙️ 文件管理"])
    
    with tab1:
        # 使用与搜索测试相同的布局比例
        col0, col1, col2 = st.columns([1, 3, 1])

        with col1:
            # OCR文件选择
            ocr_files = get_available_ocr_files()
            if not ocr_files:
                st.error("❌ 未找到OCR文件，请将JSON文件放入 ocr_files/ 目录")
                return

            selected_ocr_file = st.selectbox(
                "选择OCR文件",
                options=ocr_files,
                format_func=lambda x: os.path.basename(x)
            )

            # 创建索引按钮
            if st.button("🚀 创建索引", type="primary"):
                with st.spinner("正在创建索引..."):
                    try:
                        # 调用索引生成函数
                        result = generate_ocr_index(selected_ocr_file, "water_engineering", model_id)

                        if result:
                            st.success("✅ 索引创建成功！")

                            # 显示结果信息
                            col_info1, col_info2 = st.columns(2)
                            with col_info1:
                                st.metric("文档页数", result.get('total_pages', 0))
                                st.metric("索引节点数", len(result.get('structure', [])))
                                st.metric("表格数量", result.get('total_tables', 0))

                            with col_info2:
                                # 显示索引创建的统计信息
                                indexing_stats = result.get('indexing_stats', {})
                                if indexing_stats:
                                    st.metric("模型调用次数", indexing_stats.get('total_calls', 0))
                                    st.metric("成功调用", indexing_stats.get('success_calls', 0))
                                    st.metric("总耗时", f"{indexing_stats.get('total_time', 0):.2f}秒")
                                    st.metric("总Token使用", indexing_stats.get('total_tokens', 0))
                                else:
                                    st.metric("模型调用次数", 0)
                                    st.metric("成功调用", 0)
                                    st.metric("总耗时", "0.00秒")
                                    st.metric("总Token使用", 0)

                            st.rerun()
                        else:
                            st.error("❌ 索引创建失败")

                    except Exception as e:
                        st.error(f"❌ 索引创建失败: {str(e)}")

            # 显示可用的索引文件
            st.subheader("📁 生成的索引文件")
            index_files = get_available_index_files()

            if index_files:
                for index_file in index_files:
                    file_name = os.path.basename(index_file)
                    st.text(file_name)
            else:
                st.info("暂无索引文件")
    
    with tab2:
        
        col0, col1, col2 = st.columns([1, 3,1])
        
        with col1:
            # 索引文件选择
            index_files = get_available_index_files()
            if not index_files:
                st.error("❌ 未找到索引文件，请先生成索引")
                return
            
            selected_index_file = st.selectbox(
                "选择索引文件",
                options=index_files,
                format_func=lambda x: os.path.basename(x)
            )
            
            # OCR文件选择
            ocr_files = get_available_ocr_files()
            if not ocr_files:
                st.error("❌ 未找到OCR文件")
                return
            
            selected_ocr_file = st.selectbox(
                "选择OCR文件",
                options=ocr_files,
                format_func=lambda x: os.path.basename(x),
                key="search_ocr_file"
            )
            
            # 查询输入
            query = st.text_area(
                "输入查询问题",
                placeholder="例如：瀑布沟水电站的总库容是多少立方米？",
                height=100
            )
            
            # 搜索按钮
            if st.button("🔍 开始搜索", type="primary"):
                if not query:
                    st.error("❌ 请输入查询问题")
                else:
                    with st.spinner("正在搜索..."):
                        try:
                            # 记录开始时间
                            start_time = time.time()
                            
                            # 调用搜索函数
                            result = search_with_llm(selected_index_file, selected_ocr_file, query, model_id, "water_engineering")
                            
                            # 计算总耗时
                            total_time = time.time() - start_time
                            
                            # 保存结果到session_state
                            st.session_state.search_result = result
                            
                            if result and result.get('success'):
                                # 获取统计信息
                                stats = manager.get_stats(model_id)
                                model_stats = stats.get(model_id)
                                
                                st.success(f"✅ 搜索成功！耗时: {total_time:.2f}秒")

                                # 简化的模型调用统计
                                call_details = result.get('call_details', [])
                                if call_details:
                                    st.subheader("📊 模型调用统计")

                                    # 创建简洁的统计表格
                                    import pandas as pd
                                    stats_data = []
                                    total_input_tokens = 0
                                    total_output_tokens = 0
                                    total_time = 0

                                    for i, detail in enumerate(call_details, 1):
                                        input_tokens = detail.get('input_tokens', 0)
                                        output_tokens = detail.get('output_tokens', 0)
                                        time_taken = detail.get('elapsed_time', 0)

                                        stats_data.append({
                                            "调用": f"第{i}次",
                                            "步骤": detail.get('step', '未知'),
                                            "耗时(秒)": f"{time_taken:.2f}",
                                            "输入Token": input_tokens,
                                            "输出Token": output_tokens,
                                            "总Token": input_tokens + output_tokens
                                        })

                                        total_input_tokens += input_tokens
                                        total_output_tokens += output_tokens
                                        total_time += time_taken

                                    # 显示统计表格
                                    df = pd.DataFrame(stats_data)
                                    st.dataframe(df, width='stretch')

                                    # 显示汇总信息
                                    st.info(f"""
                                    **汇总统计:**
                                    - 总调用次数: {len(call_details)}
                                    - 总耗时: {total_time:.2f}秒
                                    - 总输入Token: {total_input_tokens:,}
                                    - 总输出Token: {total_output_tokens:,}
                                    - 总Token使用: {total_input_tokens + total_output_tokens:,}
                                    """)
                                
                                # 显示相关章节
                                if result.get('relevant_chapters'):
                                    st.subheader("📋 相关章节")
                                    for i, chapter in enumerate(result['relevant_chapters'], 1):
                                        st.text(f"{i}. {chapter.get('title', '未知标题')}")
                                
                                # 显示回答
                                st.subheader("💡 回答")
                                st.markdown(result.get('answer', '无回答'))
                                
                            else:
                                error_msg = result.get('error', '未知错误') if result else '搜索失败'
                                st.error(f"❌ 搜索失败: {error_msg}")
                                
                        except Exception as e:
                            st.error(f"❌ 搜索失败: {str(e)}")

    with tab3:
        st.header("⚙️ 文件管理和配置编辑")

        # OCR文件和索引文件管理
        st.subheader("📁 OCR文件和索引文件管理")

        # 选择管理的目录
        management_dirs = ["ocr_files", "results"]
        selected_management_dir = st.selectbox(
            "选择要管理的目录",
            management_dirs,
            format_func=lambda x: "📄 OCR文件目录" if x == "ocr_files" else "📊 索引结果目录"
        )

        # 文件列表展示
        st.subheader(f"📋 {selected_management_dir} 目录文件列表")

        if os.path.exists(selected_management_dir):
            files = [f for f in os.listdir(selected_management_dir)
                    if os.path.isfile(os.path.join(selected_management_dir, f))]
            if files:
                # 创建文件列表表格
                file_info = []
                for file in files:
                    file_path = os.path.join(selected_management_dir, file)
                    file_size = os.path.getsize(file_path)
                    file_mtime = os.path.getmtime(file_path)
                    from datetime import datetime
                    file_time = datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M:%S')

                    file_info.append({
                        "文件名": file,
                        "大小(KB)": f"{file_size/1024:.1f}",
                        "修改时间": file_time
                    })

                # 显示文件表格
                import pandas as pd
                df = pd.DataFrame(file_info)
                st.dataframe(df, width='stretch')

                # 文件操作区域
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.subheader("📤 上传文件")
                    uploaded_file = st.file_uploader(
                        f"上传到 {selected_management_dir}",
                        type=["json"] if selected_management_dir == "ocr_files" else ["json"],
                        key=f"upload_{selected_management_dir}"
                    )

                    if uploaded_file is not None:
                        if st.button(f"📤 上传到 {selected_management_dir}", key=f"upload_btn_{selected_management_dir}"):
                            try:
                                file_path = os.path.join(selected_management_dir, uploaded_file.name)
                                with open(file_path, "wb") as f:
                                    f.write(uploaded_file.getbuffer())

                                st.success(f"✅ 文件已上传: {uploaded_file.name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 上传失败: {str(e)}")

                with col2:
                    st.subheader("📥 下载文件")
                    if files:
                        selected_download_file = st.selectbox(
                            "选择要下载的文件",
                            files,
                            key=f"download_{selected_management_dir}"
                        )

                        if selected_download_file:
                            file_path = os.path.join(selected_management_dir, selected_download_file)
                            with open(file_path, "rb") as f:
                                file_data = f.read()

                            st.download_button(
                                label="📥 下载文件",
                                data=file_data,
                                file_name=selected_download_file,
                                mime="application/json",
                                key=f"download_btn_{selected_management_dir}"
                            )

                with col3:
                    st.subheader("🗑️ 删除文件")
                    if files:
                        selected_delete_file = st.selectbox(
                            "选择要删除的文件",
                            files,
                            key=f"delete_{selected_management_dir}"
                        )

                        if selected_delete_file:
                            # 显示文件详细信息
                            file_path = os.path.join(selected_management_dir, selected_delete_file)
                            file_size = os.path.getsize(file_path)
                            file_mtime = os.path.getmtime(file_path)
                            from datetime import datetime
                            file_time = datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M:%S')

                            st.info(f"""
                            **文件信息:**
                            - 文件名: {selected_delete_file}
                            - 大小: {file_size/1024:.1f} KB
                            - 修改时间: {file_time}
                            """)

                            if st.button("🗑️ 确认删除", type="secondary", key=f"delete_btn_{selected_management_dir}"):
                                try:
                                    os.remove(file_path)
                                    st.success(f"✅ 已删除: {selected_delete_file}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 删除失败: {str(e)}")
            else:
                st.info(f"📂 {selected_management_dir} 目录下暂无文件")

                # 空目录下的上传功能
                st.subheader("📤 上传文件")
                uploaded_file = st.file_uploader(
                    f"上传到 {selected_management_dir}",
                    type=["json"] if selected_management_dir == "ocr_files" else ["json"],
                    key=f"upload_empty_{selected_management_dir}"
                )

                if uploaded_file is not None:
                    if st.button(f"📤 上传到 {selected_management_dir}", key=f"upload_empty_btn_{selected_management_dir}"):
                        try:
                            file_path = os.path.join(selected_management_dir, uploaded_file.name)
                            with open(file_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())

                            st.success(f"✅ 文件已上传: {uploaded_file.name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 上传失败: {str(e)}")
        else:
            st.error(f"❌ 目录不存在: {selected_management_dir}")
            # 创建目录的选项
            if st.button(f"📁 创建目录 {selected_management_dir}"):
                try:
                    os.makedirs(selected_management_dir, exist_ok=True)
                    st.success(f"✅ 已创建目录: {selected_management_dir}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 创建目录失败: {str(e)}")

        # 配置文件说明
        st.subheader("📋 配置文件说明")
        st.info("""
        🔧 **配置文件位置**: 通过挂载方式管理配置文件
        - `model_configs.yaml` - 模型配置
        - `prompt_config.yaml` - 提示词配置

        💡 **更新配置后**: 请点击侧边栏的"更新配置"按钮重新加载配置
        """)


if __name__ == "__main__":
    main()
