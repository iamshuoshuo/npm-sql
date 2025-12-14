#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自然语言转SQL API接口

提供HTTP API接口，允许其他程序调用自然语言转SQL功能
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from nl_to_sql import DeepSeekNLtoSQL, get_table_info_from_db

app = Flask(__name__, static_folder='static')
CORS(app)  # 启用CORS支持

# 全局配置
CONFIG_FILE = "config.json"
config = None


def load_config(config_file=CONFIG_FILE):
    """加载配置"""
    global config
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"已从 {config_file} 加载配置")
    except Exception as e:
        print(f"加载配置文件时出错: {str(e)}")
        config = {
            "host": "localhost",
            "user": "root",
            "password": "root",
            "database": "selldata",
            "port": 3306,
            "deepseek_api_key": ""
        }
    return config


@app.route('/api/nl2sql', methods=['POST'])
def nl_to_sql():
    """
    自然语言转SQL API

    请求格式:
    {
        "query": "自然语言查询",
        "get_schema": true/false,  # 是否获取数据库表结构
        "execute": true/false      # 是否执行生成的SQL
    }

    响应格式:
    {
        "success": true/false,
        "sql": "生成的SQL",
        "explanation": "SQL解释",
        "schema": [...],           # 如果get_schema为true
        "results": [...]           # 如果execute为true
    }
    """
    global config

    # 确保配置已加载
    if config is None:
        config = load_config()

    # 获取请求数据
    data = request.json
    if not data or 'query' not in data:
        return jsonify({
            "success": False,
            "error": "缺少必要参数: query"
        }), 400

    natural_language = data['query']
    get_schema = data.get('get_schema', False)
    execute_sql = data.get('execute', False)

    # 设置API密钥
    api_key = config.get('deepseek_api_key', '') or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return jsonify({
            "success": False,
            "error": "未设置DeepSeek API密钥"
        }), 400

    # 获取表结构信息
    table_info = []
    if get_schema:
        try:
            table_info = get_table_info_from_db(config)
        except Exception as e:
            print(f"获取表结构信息时出错: {str(e)}")

    # 转换为SQL
    try:
        converter = DeepSeekNLtoSQL(api_key)
        sql, explanation = converter.convert_to_sql(natural_language, table_info)

        response = {
            "success": True,
            "sql": sql,
            "explanation": explanation
        }

        # 添加表结构信息
        if get_schema:
            response["schema"] = table_info

        # 执行SQL
        if execute_sql and sql:
            try:
                # 直接使用MCP客户端执行SQL
                import asyncio
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client

                # 定义异步函数执行SQL
                async def execute_sql_with_mcp():
                    # 设置环境变量
                    env = {
                        "MYSQL_HOST": config["host"],
                        "MYSQL_USER": config["user"],
                        "MYSQL_PASSWORD": config["password"],
                        "MYSQL_DATABASE": config["database"],
                        "MYSQL_PORT": str(config["port"]),
                    }

                    # 创建服务器参数
                    server_params = StdioServerParameters(
                        command="node",
                        args=["build/index.js"],
                        env=env,
                    )

                    # 连接到MCP服务器
                    async with stdio_client(server_params) as (read, write):
                        async with ClientSession(read, write) as session:
                            # 初始化会话
                            await session.initialize()

                            # 连接到数据库
                            connect_args = {
                                "host": config["host"],
                                "user": config["user"],
                                "password": config["password"],
                                "database": config["database"],
                                "port": config["port"]
                            }

                            await session.call_tool("connect_db", arguments=connect_args)

                            # 根据SQLl类型选择工具
                            if sql.strip().upper().startswith("SELECT"):
                                tool_name = "query"
                            else:
                                tool_name = "execute"

                            # 执行SQL
                            sql_args = {
                                "sql": sql,
                                "params": []
                            }

                            result = await session.call_tool(tool_name, arguments=sql_args)

                            # 提取结果
                            if hasattr(result, 'content') and result.content:
                                for item in result.content:
                                    if hasattr(item, 'text'):
                                        return item.text

                            return None

                # 执行异步函数
                result_text = asyncio.run(execute_sql_with_mcp())

                # 处理结果
                if result_text:
                    try:
                        results = json.loads(result_text)
                        response["results"] = results
                    except json.JSONDecodeError:
                        response["results"] = result_text
                else:
                    response["execute_error"] = "执行SQL未返回结果"

            except Exception as e:
                response["execute_error"] = str(e)

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/schema', methods=['GET'])
def get_schema():
    """
    获取数据库表结构

    响应格式:
    {
        "success": true/false,
        "schema": [...]
    }
    """
    global config

    # 确保配置已加载
    if config is None:
        config = load_config()

    try:
        table_info = get_table_info_from_db(config)
        return jsonify({
            "success": True,
            "schema": table_info
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    """
    获取或更新配置

    GET: 获取当前配置
    POST: 更新配置
    """
    global config

    # 确保配置已加载
    if config is None:
        config = load_config()

    if request.method == 'GET':
        # 返回配置（隐藏密码和API密钥）
        safe_config = config.copy()
        if 'password' in safe_config:
            safe_config['password'] = '******'
        if 'deepseek_api_key' in safe_config:
            safe_config['deepseek_api_key'] = '******'

        return jsonify({
            "success": True,
            "config": safe_config
        })

    elif request.method == 'POST':
        # 更新配置
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "缺少配置数据"
            }), 400

        # 更新配置
        for key, value in data.items():
            if key in config:
                config[key] = value

        # 保存配置
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

            return jsonify({
                "success": True,
                "message": "配置已更新"
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"保存配置失败: {str(e)}"
            }), 500


@app.route('/')
def index():
    """返回首页"""
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """返回静态文件"""
    return send_from_directory('static', path)

if __name__ == '__main__':
    # 加载配置
    config = load_config()

    # 设置端口
    port = int(os.environ.get('PORT', 5000))

    # 启动服务器
    app.run(host='0.0.0.0', port=port, debug=True)
