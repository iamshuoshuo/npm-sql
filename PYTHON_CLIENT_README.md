# MySQL MCP Python 客户端

这是一个Python客户端，用于连接和使用MCP MySQL服务器。它允许您通过Python代码与MySQL数据库进行交互，利用Model Context Protocol (MCP)作为中间层。

## 安装

1. 确保您已安装Node.js和npm（用于运行MCP MySQL服务器）
2. 安装Python依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本用法

```python
import asyncio
from mysql_mcp_client import MySQLMcpClient

async def main():
    # 设置环境变量
    env = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USER": "your_user",
        "MYSQL_PASSWORD": "your_password",
        "MYSQL_DATABASE": "your_database",
    }
    
    # 创建客户端并连接
    async with MySQLMcpClient(env=env) as client:
        # 连接到数据库
        await client.connect_db(
            host="localhost",
            user="your_user",
            password="your_password",
            database="your_database"
        )
        
        # 执行查询
        results = await client.query("SELECT * FROM users LIMIT 10")
        print(results)
        
        # 执行更新
        result = await client.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            ["John Doe", "john@example.com"]
        )
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

### 可用方法

客户端提供以下方法：

- `connect_db(host, user, password, database, port=None)` - 连接到MySQL数据库
- `query(sql, params=None)` - 执行SELECT查询
- `execute(sql, params=None)` - 执行INSERT, UPDATE或DELETE查询
- `list_tables()` - 列出数据库中的所有表
- `describe_table(table)` - 获取表结构

## 示例

查看 `simple_example.py` 文件，了解如何使用此客户端的完整示例。

## 工作原理

此客户端使用Python的MCP SDK与MCP MySQL服务器通信。它通过stdio与服务器进程交互，发送请求并接收响应。

MCP MySQL服务器是一个Node.js应用程序，它提供了一个标准化的接口，允许AI模型和其他应用程序与MySQL数据库交互。

## 注意事项

- 确保您的MySQL服务器正在运行并且可以访问
- 使用参数化查询（通过params参数）来防止SQL注入
- 客户端使用异步上下文管理器模式，确保资源正确清理

## 依赖

- Python 3.10+
- MCP Python SDK
- Node.js和npm（用于运行MCP MySQL服务器）
