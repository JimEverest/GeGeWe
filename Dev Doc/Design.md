GeWechat Web 设计文档

## 架构设计

### 总体架构

GeWechat Web采用现代Web应用典型的三层架构:

1. **表示层**: Web界面，负责与用户交互
2. **业务层**: FastAPI应用，处理业务逻辑
3. **数据层**: SQLite数据库，存储应用数据

### 技术选型

- **后端框架**: FastAPI - 高性能异步框架，自动生成API文档
- **数据库ORM**: SQLAlchemy - 功能强大的ORM工具
- **数据库**: SQLite - 轻量级文件数据库，便于部署
- **实时通信**: WebSockets - 提供消息实时推送
- **认证机制**: 基于会话的认证系统
- **前端**: 原生JS + CSS - 轻量级，无框架依赖

## 数据模型

### 主要实体

1. **User**: 系统用户
   - 用户名、权限等基本信息

2. **WechatAccount**: 微信账号
   - 登录状态、账号信息、关联用户

3. **Contact**: 联系人
   - 微信ID、昵称、头像等信息

4. **Group**: 群组
   - 群ID、名称、成员列表

5. **Message**: 消息
   - 发送方、接收方、内容、类型等

6. **MediaFile**: 媒体文件
   - 文件类型、URL、本地路径等

### 关系设计

- User (1) ---> (N) WechatAccount: 一个用户可有多个微信账号
- WechatAccount (1) ---> (N) Contact: 一个账号有多个联系人
- WechatAccount (1) ---> (N) Group: 一个账号有多个群组
- WechatAccount (1) ---> (N) Message: 一个账号有多条消息
- Message (1) ---> (N) MediaFile: 一条消息可含多个媒体文件

## API设计

### 主要接口

1. **认证接口**
   - `/api/auth/login`: 用户登录
   - `/api/auth/logout`: 用户登出

2. **微信接口**
   - `/wechat/token`: 获取/更新Gewechat Token
   - `/wechat/qrcode`: 获取登录二维码
   - `/wechat/login/status`: 检查登录状态
   - `/wechat/contacts`: 获取联系人列表
   - `/wechat/message/*`: 发送各类消息

3. **回调接口**
   - `/callback/message`: 接收Gewechat消息回调

4. **WebSocket接口**
   - `/ws/chat`: 聊天WebSocket连接

## 功能流程

### 登录流程

1. 用户登录系统
2. 请求微信登录二维码
3. 用户扫码
4. 系统轮询检查登录状态
5. 登录成功后初始化联系人和群组

### 消息接收流程

1. 接收回调消息
2. 存储到数据库
3. 消息分类处理
4. 通过WebSocket推送到前端
5. 前端更新聊天界面

### 消息发送流程

1. 用户在前端发送消息
2. 通过API请求发送
3. 后端调用Gewechat API发送
4. 接收发送状态回调
5. 更新前端消息状态

## 安全考虑

1. **认证与授权**
   - 使用会话Cookie进行认证
   - 权限分级控制

2. **数据安全**
   - 敏感数据加密存储
   - 密码哈希处理

3. **API安全**
   - API访问权限控制
   - CORS策略配置

## 扩展性考虑

1. **模块化设计**
   - 功能模块独立封装
   - 便于添加新功能

2. **数据库扩展**
   - ORM抽象数据访问
   - 支持未来切换数据库类型

3. **多账号支持**
   - 数据模型支持多账号
   - 界面设计考虑多账号切换
