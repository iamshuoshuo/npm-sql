#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动自然语言转SQL API服务器
"""

import os
import sys
import subprocess
import time

def check_dependencies():
    """检查依赖"""
    try:
        import flask
        print("Flask已安装")
    except ImportError:
        print("安装Flask...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
        print("Flask安装完成")

def start_server():
    """启动服务器"""
    print("启动API服务器...")
    
    # 设置环境变量
    env = os.environ.copy()
    env["PORT"] = "5000"
    
    # 启动服务器
    server_process = subprocess.Popen(
        [sys.executable, "nl_to_sql_api.py"],
        env=env
    )
    
    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(2)
    
    # 检查服务器是否启动
    try:
        import requests
        response = requests.get("http://localhost:5000/api/config")
        if response.status_code == 200:
            print("服务器已启动，可以通过以下地址访问:")
            print("http://localhost:5000/api/nl2sql")
            print("http://localhost:5000/api/schema")
            print("http://localhost:5000/api/config")
        else:
            print(f"服务器启动失败: {response.status_code}")
    except Exception as e:
        print(f"检查服务器状态时出错: {str(e)}")
    
    return server_process

if __name__ == "__main__":
    # 检查依赖
    check_dependencies()
    
    # 启动服务器
    server_process = start_server()
    
    try:
        # 保持脚本运行
        print("按Ctrl+C停止服务器")
        server_process.wait()
    except KeyboardInterrupt:
        print("停止服务器...")
        server_process.terminate()
        server_process.wait()
        print("服务器已停止")
