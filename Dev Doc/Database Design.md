# GeWechat Web 数据库设计文档

## 概述

GeWechat Web客户端使用SQLite数据库存储微信账号信息、联系人、消息记录等数据。本文档详细描述了数据库模型的设计和字段定义，为开发和维护提供参考。

## 数据库模型

### 1. WechatAccount (微信账号表)

**描述**: 存储微信账号相关信息，包括登录状态、Token等。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Integer | 账号ID | 主键, 自增 |
| appid | String | 应用ID，由GeWechat API分配 | 唯一 |
| wxid | String | 微信ID | 可空 |
| nickname | String | 昵称 | 可空 |
| avatar | String | 头像URL | 可空 |
| token | String | GeWechat API Token | 可空 |
| status | Integer | 账号状态(0:未登录,1:已登录) | 默认0 |
| last_online | DateTime | 最后在线时间 | 可空 |
| created_at | DateTime | 创建时间 | 非空 |
| updated_at | DateTime | 更新时间 | 可空 |

**关系**:
- 一个微信账号有多个联系人 (1:N → Contact)
- 一个微信账号有多条消息记录 (1:N → Message)

### 2. Contact (联系人表)

**描述**: 存储联系人信息，包括好友、群聊等。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Integer | 联系人ID | 主键, 自增 |
| account_id | Integer | 关联的账号ID | 外键(WechatAccount.id) |
| wxid | String | 联系人微信ID | 非空 |
| nickname | String | 昵称 | 可空 |
| remark | String | 备注名 | 可空 |
| avatar | String | 头像URL | 可空 |
| type | Integer | 类型(1:好友,2:群聊) | 默认1 |
| is_starred | Boolean | 是否星标联系人 | 默认False |
| created_at | DateTime | 创建时间 | 非空 |
| updated_at | DateTime | 更新时间 | 可空 |

**关系**:
- 属于一个微信账号 (N:1 → WechatAccount)
- 一个联系人有多条消息记录 (1:N → Message)
- 一个群聊有多个群成员 (1:N → GroupMember，若type=2)

### 3. GroupMember (群成员表)

**描述**: 存储群聊成员信息。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Integer | 群成员ID | 主键, 自增 |
| group_id | Integer | 关联的群ID | 外键(Contact.id) |
| member_wxid | String | 成员微信ID | 非空 |
| nickname | String | 群内昵称 | 可空 |
| account_id | Integer | 关联的账号ID | 外键(WechatAccount.id) |
| created_at | DateTime | 创建时间 | 非空 |
| updated_at | DateTime | 更新时间 | 可空 |

**关系**:
- 属于一个群 (N:1 → Contact)
- 与一个微信账号关联 (N:1 → WechatAccount)

### 4. Message (消息表)

**描述**: 存储消息记录。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Integer | 消息ID | 主键, 自增 |
| msg_id | String | 微信消息ID | 可空 |
| new_msg_id | String | 新消息ID，用于排重 | 可空 |
| app_id | String | 关联的应用ID | 可空 |
| from_wxid | String | 发送者微信ID | 非空 |
| to_wxid | String | 接收者微信ID | 非空 |
| content | Text | 消息内容 | 可空 |
| type | Integer | 消息类型(1:文本,3:图片,等) | 默认1 |
| status | Integer | 消息状态(0:未读,1:已读,等) | 默认0 |
| created_at | DateTime | 创建时间 | 非空 |
| raw_data | Text | 原始消息数据(JSON格式) | 可空 |
| media_url | String | 媒体文件URL | 可空 |

**关系**:
- 与一个微信账号关联 (N:1 → WechatAccount，通过app_id间接关联)
- 一条消息可能有一个媒体文件 (1:1 → MediaFile，对于媒体消息)

### 5. MediaFile (媒体文件表)

**描述**: 存储媒体文件信息，如图片、语音、视频等。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | Integer | 文件ID | 主键, 自增 |
| msg_id | Integer | 关联的消息ID | 外键(Message.id) |
| file_type | Integer | 文件类型(1:图片,2:视频,等) | 非空 |
| file_url | String | 文件URL | 可空 |
| thumb_url | String | 缩略图URL | 可空 |
| aes_key | String | 文件加密密钥 | 可空 |
| file_id | String | 文件唯一标识 | 可空 |
| local_path | String | 本地文件路径 | 可空 |
| created_at | DateTime | 创建时间 | 非空 |

**关系**:
- 属于一条消息 (N:1 → Message)

## 索引设计

为提高查询效率，设计了以下索引：

1. WechatAccount表:
   - appid索引 (唯一索引)
   - wxid索引

2. Contact表:
   - (account_id, wxid)复合索引 (唯一索引)
   - wxid索引

3. Message表:
   - (app_id, new_msg_id)复合索引 (用于消息排重)
   - from_wxid索引
   - to_wxid索引
   - created_at索引 (用于时间排序)

4. GroupMember表:
   - (group_id, member_wxid)复合索引 (唯一索引)

## 表关系图

```
WechatAccount 1 ------< Contact
       |                  |
       |                  | (type=2)
       |                  |
       |              1   v
       |            ------< GroupMember
       |
       |
       |
1 <----
Message >------< MediaFile
```

## 数据存储注意事项

1. **消息排重**: 使用app_id + new_msg_id组合进行消息排重，防止重复保存相同消息。

2. **媒体文件存储**: 媒体文件保存在本地文件系统中，数据库只存储文件路径和相关元数据。

3. **消息内容加密**: 敏感消息内容可以考虑加密存储，增强安全性。

4. **数据备份**: 定期备份数据库文件，防止数据丢失。

## 优化建议

1. **分表存储**: 如果消息量大，可以考虑按时间或会话分表存储消息。

2. **索引优化**: 根据实际查询模式调整索引，提高查询效率。

3. **清理机制**: 设计合理的数据清理机制，避免数据库无限增长。

4. **消息缓存**: 对频繁访问的最近消息使用内存缓存，减少数据库访问。

此数据库设计围绕微信通信的核心功能展开，支持账号管理、联系人管理和消息处理等基本功能，为GeWechat Web客户端提供了可靠的数据存储基础。
v