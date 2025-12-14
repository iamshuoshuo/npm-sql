#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接到MySQL数据库的脚本
"""

import asyncio
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_connect(host, user, password, database, port):
    """连接到数据库"""
    # 设置环境变量
    env = {
        "MYSQL_HOST": host,
        "MYSQL_USER": user,
        "MYSQL_PASSWORD": password,
        "MYSQL_DATABASE": database,
        "MYSQL_PORT": str(port),
    }
    
    # 创建服务器参数
    server_params = StdioServerParameters(
        command="node",
        args=["build/index.js"],
        env=env,
    )
    
    try:
        print("连接到MCP服务器...")
        async with stdio_client(server_params) as (read, write):
            print("成功连接到MCP服务器")
            
            async with ClientSession(read, write) as session:
                print("初始化会话...")
                await session.initialize()
                print("会话初始化成功")
                
                # 连接到数据库
                print("\n连接到数据库...")
                connect_args = {
                    "host": host,
                    "user": user,
                    "password": password,
                    "database": database,
                    "port": port
                }
                
                result = await session.call_tool("connect_db", arguments=connect_args)
                print("连接结果:")
                if hasattr(result, "content") and result.content:
                    for item in result.content:
                        if hasattr(item, "text"):
                            print(item.text)
    
    except Exception as e:
        print(f"执行过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) >= 6:
        host = sys.argv[1]
        user = sys.argv[2]
        password = sys.argv[3]
        database = sys.argv[4]
        port = int(sys.argv[5])
        asyncio.run(run_connect(host, user, password, database, port))
    else:
        print("用法: python connect_db.py <host> <user> <password> <database> <port>")
        sys.exit(1)
