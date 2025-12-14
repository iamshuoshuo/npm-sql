#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自然语言转SQL模块 - 使用DeepSeek AI将自然语言转换为SQL查询
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List, Tuple


class DeepSeekNLtoSQL:
    """DeepSeek AI自然语言转SQL类"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化DeepSeek AI客户端

        Args:
            api_key: DeepSeek API密钥，如果为None则从环境变量获取
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未提供，请设置DEEPSEEK_API_KEY环境变量或在初始化时提供")

        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def convert_to_sql(self, natural_language: str, table_info: Optional[List[Dict[str, Any]]] = None) -> Tuple[str, str]:
        """
        将自然语言转换为SQL查询

        Args:
            natural_language: 自然语言查询
            table_info: 表结构信息，用于提供上下文

        Returns:
            Tuple[str, str]: (SQL查询, 解释)
        """
        # 构建提示
        system_prompt = "你是一个专业的SQL专家，擅长将自然语言转换为SQL查询。请根据用户的自然语言描述，生成对应的SQL查询语句。"

        if table_info:
            system_prompt += "\n\n数据库表结构信息如下:\n"
            for table in table_info:
                system_prompt += f"\n表名: {table['name']}\n"
                system_prompt += "列:\n"
                for column in table['columns']:
                    system_prompt += f"- {column['name']}: {column['type']}"
                    if column.get('description'):
                        system_prompt += f" ({column['description']})"
                    system_prompt += "\n"

        user_prompt = f"请将以下自然语言转换为SQL查询:\n\n{natural_language}\n\n请只返回SQL查询语句和简短解释，不要包含其他内容。格式如下:\n\nSQL: [SQL查询语句]\n解释: [简短解释]"

        # 构建请求
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,  # 低温度以获得更确定性的结果
            "max_tokens": 1000
        }

        # 发送请求
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()

            # 解析响应
            content = result["choices"][0]["message"]["content"]

            # 提取SQL和解释
            sql = ""
            explanation = ""

            if "SQL:" in content and "解释:" in content:
                parts = content.split("解释:")
                sql_part = parts[0].strip()
                sql = sql_part.replace("SQL:", "").strip()
                explanation = parts[1].strip()
            else:
                # 尝试其他格式
                lines = content.split("\n")
                for line in lines:
                    if line.startswith("SQL:"):
                        sql = line.replace("SQL:", "").strip()
                    elif line.startswith("解释:"):
                        explanation = line.replace("解释:", "").strip()

            # 清理SQL中的Markdown代码块标记
            sql = sql.replace("```sql", "").replace("```", "").strip()

            return sql, explanation

        except Exception as e:
            print(f"调用DeepSeek API时出错: {str(e)}")
            return "", f"错误: {str(e)}"


def get_table_info_from_db(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从数据库获取表结构信息

    Args:
        config: 数据库配置

    Returns:
        表结构信息列表
    """

    import asyncio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def get_tables_info():
        tables_info = []

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

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
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

                    # 列出所有表
                    tables_result = await session.call_tool("list_tables", arguments={})
                    tables_text = ""
                    if hasattr(tables_result, 'content') and tables_result.content:
                        for item in tables_result.content:
                            if hasattr(item, 'text'):
                                tables_text = item.text

                    tables_data = json.loads(tables_text)
                    table_names = []
                    for table_info in tables_data:
                        for key in table_info:
                            if key.startswith("Tables_in_"):
                                table_names.append(table_info[key])

                    # 获取每个表的结构
                    for table_name in table_names:
                        describe_args = {"table": table_name}
                        describe_result = await session.call_tool("describe_table", arguments=describe_args)
                        describe_text = ""
                        if hasattr(describe_result, 'content') and describe_result.content:
                            for item in describe_result.content:
                                if hasattr(item, 'text'):
                                    describe_text = item.text

                        columns_data = json.loads(describe_text)
                        columns = []
                        for column_info in columns_data:
                            column = {
                                "name": column_info["Field"],
                                "type": column_info["Type"],
                                "description": f"{'主键' if column_info['Key'] == 'PRI' else ''} {'可为空' if column_info['Null'] == 'YES' else '不可为空'}"
                            }
                            columns.append(column)

                        table_info = {
                            "name": table_name,
                            "columns": columns
                        }
                        tables_info.append(table_info)

        except Exception as e:
            print(f"获取表结构信息时出错: {str(e)}")

        return tables_info

    return asyncio.run(get_tables_info())


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python nl_to_sql.py \"自然语言查询\"")
        sys.exit(1)

    # 从环境变量获取API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误: 未设置DEEPSEEK_API_KEY环境变量")
        sys.exit(1)

    # 创建转换器
    converter = DeepSeekNLtoSQL(api_key)

    # 获取自然语言查询
    natural_language = sys.argv[1]

    # 转换为SQL
    sql, explanation = converter.convert_to_sql(natural_language)

    print(f"自然语言: {natural_language}")
    print(f"SQL: {sql}")
    print(f"解释: {explanation}")
