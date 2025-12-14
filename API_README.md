# 自然语言转SQL API

这个API允许其他程序通过HTTP接口调用自然语言转SQL功能。

## 文件说明

- `nl_to_sql_api.py` - API服务器
- `nl_to_sql_client.py` - Python客户端库
- `nl_to_sql_example.py` - 使用示例
- `start_api_server.py` - 启动API服务器的脚本

## 启动API服务器

```bash
python start_api_server.py
```

服务器将在 http://localhost:5000 上运行。

## API接口

### 1. 自然语言转SQL

**URL:** `/api/nl2sql`

**方法:** POST

**请求格式:**
```json
{
    "query": "自然语言查询",
    "get_schema": true/false,  // 是否获取数据库表结构
    "execute": true/false      // 是否执行生成的SQL
}
```

**响应格式:**
```json
{
    "success": true/false,
    "sql": "生成的SQL",
    "explanation": "SQL解释",
    "schema": [...],           // 如果get_schema为true
    "results": [...]           // 如果execute为true
}
```

### 2. 获取数据库表结构

**URL:** `/api/schema`

**方法:** GET

**响应格式:**
```json
{
    "success": true/false,
    "schema": [...]
}
```

### 3. 管理配置

**URL:** `/api/config`

**方法:** GET/POST

**GET响应格式:**
```json
{
    "success": true/false,
    "config": {
        "host": "localhost",
        "user": "root",
        "password": "******",
        "database": "selldata",
        "port": 3306,
        "deepseek_api_key": "******"
    }
}
```

**POST请求格式:**
```json
{
    "host": "localhost",
    "user": "root",
    "password": "newpassword",
    "database": "selldata",
    "port": 3306,
    "deepseek_api_key": "your-api-key"
}
```

**POST响应格式:**
```json
{
    "success": true/false,
    "message": "配置已更新"
}
```

## 使用Python客户端库

```python
from nl_to_sql_client import NLtoSQLClient

# 创建客户端
client = NLtoSQLClient("http://localhost:5000")

# 自然语言转SQL
result = client.convert_to_sql("找到价格最高的产品")
print(f"SQL: {result['sql']}")
print(f"解释: {result['explanation']}")

# 获取表结构并执行查询
result = client.convert_to_sql("统计每个客户的订单数量", get_schema=True, execute=True)
print(f"SQL: {result['sql']}")
if "results" in result:
    print("查询结果:", result["results"])

# 获取数据库表结构
schema = client.get_schema()
if schema["success"]:
    print(f"找到 {len(schema['schema'])} 个表")

# 获取当前配置
config = client.get_config()
if config["success"]:
    print("当前配置:", config["config"])

# 更新配置
new_config = {"database": "newdb"}
result = client.update_config(new_config)
print(result["message"])
```

## 命令行使用

客户端库也可以作为命令行工具使用：

```bash
# 自然语言转SQL
python nl_to_sql_client.py --query "找到价格最高的产品"

# 获取表结构并执行查询
python nl_to_sql_client.py --query "统计每个客户的订单数量" --schema --execute

# 获取数据库表结构
python nl_to_sql_client.py --schema
```

## 集成到其他程序

### 在Python程序中集成

```python
from nl_to_sql_client import NLtoSQLClient

def process_natural_language_query(query):
    client = NLtoSQLClient()
    result = client.convert_to_sql(query, execute=True)
    if result["success"]:
        return result["results"]
    else:
        return None
```

### 在其他语言程序中集成

只需使用HTTP请求调用API接口即可。例如，在JavaScript中：

```javascript
async function convertToSQL(query) {
    const response = await fetch('http://localhost:5000/api/nl2sql', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            query: query,
            execute: true
        })
    });
    
    return await response.json();
}
```
