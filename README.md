# Gewechat Web Client

基于Gewechat API的Web微信客户端，提供扫码登录、消息收发、联系人管理等功能。

## 功能特点

- 扫码登录与状态管理
- 消息接收与发送
- 联系人与群组管理
- 多媒体消息支持

## 安装与使用

1. 克隆仓库
2. 安装依赖: `pip install -r requirements.txt`
3. 配置环境变量: 复制`.env.example`为`.env`并修改
4. 启动应用: `uvicorn app.main:app --reload`

## 技术栈

- 后端: FastAPI
- 数据库: SQLite
- 前端: 原生JS/CSS
