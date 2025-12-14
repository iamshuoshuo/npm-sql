#!/usr/bin/env python3
"""
简单的交互式MCP MySQL客户端菜单
从配置文件读取连接信息，提供菜单选择不同的功能
"""

import json
import os
import subprocess
import sys
import time
import asyncio

# 导入自然语言转SQL模块
try:
    from nl_to_sql import DeepSeekNLtoSQL, get_table_info_from_db
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False

# 导入简单持久化客户端
try:
    import simple_persistent_client as spc
    PERSISTENT_CLIENT_AVAILABLE = True
except ImportError:
    PERSISTENT_CLIENT_AVAILABLE = False


def load_config(config_file="config.json"):
    """从配置文件加载数据库连接信息"""
    # 默认配置
    config = {
        "host": "localhost",
        "user": "root",
        "password": "root",
        "database": "selldata",
        "port": 3306
    }

    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
            print(f"已从 {config_file} 加载配置")
        else:
            print(f"配置文件 {config_file} 不存在，使用默认配置")
            # 创建默认配置文件
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            print(f"已创建默认配置文件: {config_file}")
    except Exception as e:
        print(f"加载配置文件时出错: {str(e)}")
        print("使用默认配置")

    return config


def run_mysql_client(config_file="config.json"):
    """运行MySQL客户端菜单"""
    # 引用全局变量
    global PERSISTENT_CLIENT_AVAILABLE, DEEPSEEK_AVAILABLE

    # 加载配置
    config = load_config(config_file)

    # 初始化持久化客户端
    if PERSISTENT_CLIENT_AVAILABLE:
        try:
            print("初始化持久化MCP客户端...")
            if spc.connect_to_server(config):
                print("持久化客户端初始化成功")
            else:
                print("持久化客户端初始化失败")
                PERSISTENT_CLIENT_AVAILABLE = False
        except Exception as e:
            print(f"初始化持久化客户端失败: {str(e)}")
            PERSISTENT_CLIENT_AVAILABLE = False

    try:
        while True:
            # 清屏
            os.system('cls' if os.name == 'nt' else 'clear')

            print("交互式MCP MySQL客户端")
            print("=" * 50)

            print("\n当前数据库配置:")
            for key, value in config.items():
                print(f"  {key}: {value}")

            print("\n可用功能:")
            print("1. 连接到数据库")
            print("2. 执行查询 (SELECT)")
            print("3. 执行更新 (INSERT, UPDATE, DELETE)")
            print("4. 列出所有表")
            print("5. 获取表结构")
            if DEEPSEEK_AVAILABLE:
                print("6. 自然语言查询 (AI转SQL)")
                print("7. 修改数据库配置")
                print("8. 退出")
            else:
                print("6. 修改数据库配置")
                print("7. 退出")
            print("=" * 50)

            if DEEPSEEK_AVAILABLE:
                choice = input("\n请选择功能 (1-8): ")
            else:
                choice = input("\n请选择功能 (1-7): ")

            if choice == "1":
                connect_to_database(config)
            elif choice == "2":
                execute_query(config)
            elif choice == "3":
                execute_update(config)
            elif choice == "4":
                list_tables(config)
            elif choice == "5":
                describe_table(config)
            elif choice == "6":
                if DEEPSEEK_AVAILABLE:
                    natural_language_query(config)
                else:
                    config = modify_config(config, config_file)
            elif choice == "7":
                if DEEPSEEK_AVAILABLE:
                    config = modify_config(config, config_file)
                else:
                    print("退出程序...")
                    break
            elif choice == "8" and DEEPSEEK_AVAILABLE:
                print("退出程序...")
                break
            else:
                print("无效的选择，请重试")

            input("\n按回车键继续...")
    finally:
        # 清理持久化客户端
        if PERSISTENT_CLIENT_AVAILABLE:
            print("正在断开与MCP服务器的连接...")
            spc.disconnect()
            print("连接已断开")


def connect_to_database(config):
    """连接到数据库"""
    print("\n连接到数据库...")

    if PERSISTENT_CLIENT_AVAILABLE:
        # 使用持久化客户端
        if spc.connect_to_server(config):
            print("连接成功")
        else:
            print("连接失败")
    else:
        # 使用原来的方式
        try:
            cmd = [
                "python", "connect_db.py",
                config['host'],
                config['user'],
                config['password'],
                config['database'],
                str(config['port'])
            ]
            subprocess.run(cmd, check=True)
            print("连接成功")
        except subprocess.CalledProcessError as e:
            print(f"连接失败: {e}")


def execute_query(config):
    """执行查询"""
    sql = input("\n请输入SQL查询语句 (SELECT): ")
    if not sql:
        print("错误: SQL查询语句不能为空")
        return

    if not sql.strip().upper().startswith("SELECT"):
        print("错误: 只能执行SELECT查询")
        return

    if PERSISTENT_CLIENT_AVAILABLE:
        # 使用持久化客户端
        print(f"\n执行查询: {sql}")
        results = spc.query(sql)
        if results:
            print("\n查询结果:")
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print("\n查询失败")
    else:
        # 创建临时脚本
        with open("temp_query.py", "w", encoding="utf-8") as f:
            f.write(f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_query():
    # 设置环境变量
    env = {{
        "MYSQL_HOST": "{config['host']}",
        "MYSQL_USER": "{config['user']}",
        "MYSQL_PASSWORD": "{config['password']}",
        "MYSQL_DATABASE": "{config['database']}",
        "MYSQL_PORT": "{config['port']}",
    }}

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
                print("\\n连接到数据库...")
                connect_args = {{
                    "host": "{config['host']}",
                    "user": "{config['user']}",
                    "password": "{config['password']}",
                    "database": "{config['database']}",
                    "port": {config['port']}
                }}

                result = await session.call_tool("connect_db", arguments=connect_args)
                print("连接结果:")
                if hasattr(result, 'content') and result.content:
                    for item in result.content:
                        if hasattr(item, 'text'):
                            print(item.text)

                # 执行查询
                print("\\n执行查询: {sql}")
                query_args = {{
                    "sql": "{sql}",
                    "params": []
                }}

                query_result = await session.call_tool("query", arguments=query_args)
                if hasattr(query_result, 'content') and query_result.content:
                    for item in query_result.content:
                        if hasattr(item, 'text'):
                            print("\\n查询结果:")
                            try:
                                data = json.loads(item.text)
                                print(json.dumps(data, indent=2, ensure_ascii=False))
                            except:
                                print(item.text)

    except Exception as e:
        print(f"执行过程中出错: {{str(e)}}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_query())
""")

    # 执行临时脚本
    try:
        subprocess.run(["python", "temp_query.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"执行查询失败: {e}")

    # 删除临时脚本
    try:
        os.remove("temp_query.py")
    except:
        pass


def execute_update(config):
    """执行更新"""
    sql = input("\n请输入SQL语句 (INSERT, UPDATE, DELETE): ")
    if not sql:
        print("错误: SQL语句不能为空")
        return

    if sql.strip().upper().startswith("SELECT"):
        print("错误: 请使用查询功能执行SELECT语句")
        return

    if PERSISTENT_CLIENT_AVAILABLE:
        # 使用持久化客户端
        print(f"\n执行更新: {sql}")
        results = spc.execute(sql)
        if results:
            print("\n执行结果:")
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print("\n执行失败")
    else:
        # 创建临时脚本
        with open("temp_execute.py", "w", encoding="utf-8") as f:
            f.write(f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_execute():
    # 设置环境变量
    env = {{
        "MYSQL_HOST": "{config['host']}",
        "MYSQL_USER": "{config['user']}",
        "MYSQL_PASSWORD": "{config['password']}",
        "MYSQL_DATABASE": "{config['database']}",
        "MYSQL_PORT": "{config['port']}",
    }}

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
                print("\\n连接到数据库...")
                connect_args = {{
                    "host": "{config['host']}",
                    "user": "{config['user']}",
                    "password": "{config['password']}",
                    "database": "{config['database']}",
                    "port": {config['port']}
                }}

                result = await session.call_tool("connect_db", arguments=connect_args)
                print("连接结果:")
                if hasattr(result, 'content') and result.content:
                    for item in result.content:
                        if hasattr(item, 'text'):
                            print(item.text)

                # 执行更新
                print("\\n执行更新: {sql}")
                execute_args = {{
                    "sql": "{sql}",
                    "params": []
                }}

                execute_result = await session.call_tool("execute", arguments=execute_args)
                if hasattr(execute_result, 'content') and execute_result.content:
                    for item in execute_result.content:
                        if hasattr(item, 'text'):
                            print("\\n执行结果:")
                            try:
                                data = json.loads(item.text)
                                print(json.dumps(data, indent=2, ensure_ascii=False))
                            except:
                                print(item.text)

    except Exception as e:
        print(f"执行过程中出错: {{str(e)}}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_execute())
""")

    # 执行临时脚本
    try:
        subprocess.run(["python", "temp_execute.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"执行更新失败: {e}")

    # 删除临时脚本
    try:
        os.remove("temp_execute.py")
    except:
        pass


def list_tables(config):
    """列出所有表"""
    if PERSISTENT_CLIENT_AVAILABLE:
        # 使用持久化客户端
        print("\n列出所有表...")
        tables = spc.list_tables()
        if tables:
            print("\n表列表:")

            # 提取表名
            table_names = []
            for table_info in tables:
                for key in table_info:
                    if key.startswith("Tables_in_"):
                        table_names.append(table_info[key])

            # 显示表名
            for i, table in enumerate(table_names, 1):
                print(f"{i}. {table}")
        else:
            print("\n获取表列表失败")
    else:
        # 创建临时脚本
        with open("temp_list_tables.py", "w", encoding="utf-8") as f:
            f.write(f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_list_tables():
    # 设置环境变量
    env = {{
        "MYSQL_HOST": "{config['host']}",
        "MYSQL_USER": "{config['user']}",
        "MYSQL_PASSWORD": "{config['password']}",
        "MYSQL_DATABASE": "{config['database']}",
        "MYSQL_PORT": "{config['port']}",
    }}

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
                print("\\n连接到数据库...")
                connect_args = {{
                    "host": "{config['host']}",
                    "user": "{config['user']}",
                    "password": "{config['password']}",
                    "database": "{config['database']}",
                    "port": {config['port']}
                }}

                result = await session.call_tool("connect_db", arguments=connect_args)
                print("连接结果:")
                if hasattr(result, 'content') and result.content:
                    for item in result.content:
                        if hasattr(item, 'text'):
                            print(item.text)

                # 列出所有表
                print("\\n列出所有表...")
                tables_result = await session.call_tool("list_tables", arguments={{}})
                if hasattr(tables_result, 'content') and tables_result.content:
                    for item in tables_result.content:
                        if hasattr(item, 'text'):
                            print("\\n表列表:")
                            try:
                                data = json.loads(item.text)
                                # 提取表名
                                table_names = []
                                for table_info in data:
                                    for key in table_info:
                                        if key.startswith("Tables_in_"):
                                            table_names.append(table_info[key])

                                # 显示表名
                                for i, table in enumerate(table_names, 1):
                                    print(f"{{i}}. {{table}}")
                            except:
                                print(item.text)

    except Exception as e:
        print(f"执行过程中出错: {{str(e)}}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_list_tables())
""")

    # 执行临时脚本
    try:
        subprocess.run(["python", "temp_list_tables.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"列出表失败: {e}")

    # 删除临时脚本
    try:
        os.remove("temp_list_tables.py")
    except:
        pass


def describe_table(config):
    """获取表结构"""
    table = input("\n请输入表名: ")
    if not table:
        print("错误: 表名不能为空")
        return

    if PERSISTENT_CLIENT_AVAILABLE:
        # 使用持久化客户端
        print(f"\n获取表 {table} 的结构...")
        structure = spc.describe_table(table)
        if structure:
            print(f"\n表 {table} 结构:")
            print(json.dumps(structure, indent=2, ensure_ascii=False))
        else:
            print(f"\n获取表 {table} 结构失败")
    else:
        # 创建临时脚本
        with open("temp_describe_table.py", "w", encoding="utf-8") as f:
            f.write(f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_describe_table():
    # 设置环境变量
    env = {{
        "MYSQL_HOST": "{config['host']}",
        "MYSQL_USER": "{config['user']}",
        "MYSQL_PASSWORD": "{config['password']}",
        "MYSQL_DATABASE": "{config['database']}",
        "MYSQL_PORT": "{config['port']}",
    }}

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
                print("\\n连接到数据库...")
                connect_args = {{
                    "host": "{config['host']}",
                    "user": "{config['user']}",
                    "password": "{config['password']}",
                    "database": "{config['database']}",
                    "port": {config['port']}
                }}

                result = await session.call_tool("connect_db", arguments=connect_args)
                print("连接结果:")
                if hasattr(result, 'content') and result.content:
                    for item in result.content:
                        if hasattr(item, 'text'):
                            print(item.text)

                # 获取表结构
                print("\\n获取表 {table} 的结构...")
                describe_args = {{"table": "{table}"}}

                describe_result = await session.call_tool("describe_table", arguments=describe_args)
                if hasattr(describe_result, 'content') and describe_result.content:
                    for item in describe_result.content:
                        if hasattr(item, 'text'):
                            print("\\n表 {table} 结构:")
                            try:
                                data = json.loads(item.text)
                                print(json.dumps(data, indent=2, ensure_ascii=False))
                            except:
                                print(item.text)

    except Exception as e:
        print(f"执行过程中出错: {{str(e)}}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_describe_table())
""")

    # 执行临时脚本
    try:
        subprocess.run(["python", "temp_describe_table.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"获取表结构失败: {e}")

    # 删除临时脚本
    try:
        os.remove("temp_describe_table.py")
    except:
        pass


def natural_language_query(config):
    """自然语言查询"""
    # 检查API密钥
    api_key = config.get('deepseek_api_key', '') or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        api_key = input("\n请输入DeepSeek API密钥: ")
        if not api_key:
            print("错误: 需要DeepSeek API密钥")
            return
        # 设置环境变量
        os.environ["DEEPSEEK_API_KEY"] = api_key

        # 询问是否保存到配置文件
        if input("\n是否将API密钥保存到配置文件? (y/n): ").lower() == 'y':
            config['deepseek_api_key'] = api_key
            try:
                with open('config.json', 'w') as f:
                    json.dump(config, f, indent=4)
                print("API密钥已保存到配置文件")
            except Exception as e:
                print(f"保存配置文件时出错: {str(e)}")

    # 初始化持久化客户端
    if PERSISTENT_CLIENT_AVAILABLE:
        try:
            client = run_async(get_client(config))
            print("持久化客户端已就绪")
        except Exception as e:
            print(f"初始化持久化客户端失败: {str(e)}")

    # 获取自然语言查询
    natural_language = input("\n请输入自然语言查询: ")
    if not natural_language:
        print("错误: 查询不能为空")
        return

    print("\n获取数据库表结构信息...")
    table_info = get_table_info_from_db(config)

    print("\n将自然语言转换为SQL...")
    converter = DeepSeekNLtoSQL(api_key)
    sql, explanation = converter.convert_to_sql(natural_language, table_info)

    print(f"\n生成的SQL: {sql}")
    print(f"\n解释: {explanation}")

    # 询问是否执行生成的SQL
    if input("\n是否执行SQL? (y/n): ").lower() == 'y':
        # 检查SQL类型
        if sql.strip().upper().startswith("SELECT"):
            # 创建临时脚本
            with open("temp_nl_query.py", "w", encoding="utf-8") as f:
                f.write(f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_nl_query():
    # 设置环境变量
    env = {{
        "MYSQL_HOST": "{config['host']}",
        "MYSQL_USER": "{config['user']}",
        "MYSQL_PASSWORD": "{config['password']}",
        "MYSQL_DATABASE": "{config['database']}",
        "MYSQL_PORT": "{config['port']}",
    }}

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
                print("\\n连接到数据库...")
                connect_args = {{
                    "host": "{config['host']}",
                    "user": "{config['user']}",
                    "password": "{config['password']}",
                    "database": "{config['database']}",
                    "port": {config['port']}
                }}

                result = await session.call_tool("connect_db", arguments=connect_args)
                print("连接结果:")
                if hasattr(result, 'content') and result.content:
                    for item in result.content:
                        if hasattr(item, 'text'):
                            print(item.text)

                # 执行查询
                print(f"\\n执行查询: {sql.replace('\n', ' ')}")
                query_args = {{
                    "sql": '''{sql.replace("'", "\\'").replace('\n', ' ')}''',
                    "params": []
                }}

                query_result = await session.call_tool("query", arguments=query_args)
                if hasattr(query_result, 'content') and query_result.content:
                    for item in query_result.content:
                        if hasattr(item, 'text'):
                            print("\\n查询结果:")
                            try:
                                data = json.loads(item.text)
                                print(json.dumps(data, indent=2, ensure_ascii=False))
                            except:
                                print(item.text)

    except Exception as e:
        print(f"执行过程中出错: {{str(e)}}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_nl_query())
""")

            # 执行临时脚本
            try:
                subprocess.run(["python", "temp_nl_query.py"], check=True)
            except subprocess.CalledProcessError as e:
                print(f"执行查询失败: {e}")

            # 删除临时脚本
            try:
                os.remove("temp_nl_query.py")
            except:
                pass
        else:
            # 创建临时脚本
            with open("temp_nl_execute.py", "w", encoding="utf-8") as f:
                f.write(f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_nl_execute():
    # 设置环境变量
    env = {{
        "MYSQL_HOST": "{config['host']}",
        "MYSQL_USER": "{config['user']}",
        "MYSQL_PASSWORD": "{config['password']}",
        "MYSQL_DATABASE": "{config['database']}",
        "MYSQL_PORT": "{config['port']}",
    }}

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
                print("\\n连接到数据库...")
                connect_args = {{
                    "host": "{config['host']}",
                    "user": "{config['user']}",
                    "password": "{config['password']}",
                    "database": "{config['database']}",
                    "port": {config['port']}
                }}

                result = await session.call_tool("connect_db", arguments=connect_args)
                print("连接结果:")
                if hasattr(result, 'content') and result.content:
                    for item in result.content:
                        if hasattr(item, 'text'):
                            print(item.text)

                # 执行更新
                print(f"\\n执行更新: {sql.replace('\n', ' ')}")
                execute_args = {{
                    "sql": '''{sql.replace("'", "\\'").replace('\n', ' ')}''',
                    "params": []
                }}

                execute_result = await session.call_tool("execute", arguments=execute_args)
                if hasattr(execute_result, 'content') and execute_result.content:
                    for item in execute_result.content:
                        if hasattr(item, 'text'):
                            print("\\n执行结果:")
                            try:
                                data = json.loads(item.text)
                                print(json.dumps(data, indent=2, ensure_ascii=False))
                            except:
                                print(item.text)

    except Exception as e:
        print(f"执行过程中出错: {{str(e)}}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_nl_execute())
""")

            # 执行临时脚本
            try:
                subprocess.run(["python", "temp_nl_execute.py"], check=True)
            except subprocess.CalledProcessError as e:
                print(f"执行更新失败: {e}")

            # 删除临时脚本
            try:
                os.remove("temp_nl_execute.py")
            except:
                pass


def modify_config(config, config_file):
    """修改数据库连接配置"""
    print("\n修改数据库连接配置")
    print("当前配置:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    # 修改配置
    host = input(f"\n主机 [{config['host']}]: ") or config['host']
    user = input(f"用户名 [{config['user']}]: ") or config['user']
    password = input(f"密码 [{config['password']}]: ") or config['password']
    database = input(f"数据库 [{config['database']}]: ") or config['database']
    port_str = input(f"端口 [{config['port']}]: ") or str(config['port'])

    # 获取DeepSeek API密钥
    deepseek_api_key = config.get('deepseek_api_key', '')
    new_deepseek_api_key = input(f"DeepSeek API密钥 [{deepseek_api_key if deepseek_api_key else '(未设置)'}]: ") or deepseek_api_key

    try:
        port = int(port_str)
    except ValueError:
        print(f"端口必须是数字，使用默认值 {config['port']}")
        port = config['port']

    # 更新配置
    new_config = {
        "host": host,
        "user": user,
        "password": password,
        "database": database,
        "port": port,
        "deepseek_api_key": new_deepseek_api_key
    }

    # 保存配置
    try:
        with open(config_file, 'w') as f:
            json.dump(new_config, f, indent=4)
        print(f"配置已保存到 {config_file}")
    except Exception as e:
        print(f"保存配置文件时出错: {str(e)}")

    return new_config


if __name__ == "__main__":
    # 检查命令行参数
    config_file = "config.json"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    run_mysql_client(config_file)
