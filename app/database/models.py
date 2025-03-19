from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.database import Base
import datetime
from datetime import datetime as dt
import json

class User(Base):
    """用户表，存储使用本应用的用户信息"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)
    auth_level = Column(Integer, default=1)  # 权限级别：1-普通用户，2-管理员
    
    # 关联的微信账号
    wechat_accounts = relationship("WechatAccount", back_populates="user")
    
    def __repr__(self):
        return f"<User(username='{self.username}')>"

class WechatAccount(Base):
    """微信账号表，存储登录后的微信账号信息"""
    __tablename__ = "wechat_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    appid = Column(String, unique=True, index=True)
    wxid = Column(String, nullable=True)
    nickname = Column(String, nullable=True)
    avatar = Column(String, nullable=True)
    token = Column(String, nullable=True)
    status = Column(Integer, default=0)  # 0: 未登录, 1: 已登录
    login_uuid = Column(String, nullable=True)  # 保存登录二维码的UUID
    last_online = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=dt.now)
    updated_at = Column(DateTime, nullable=True, onupdate=dt.now)
    
    # 外键关联
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="wechat_accounts")
    
    # 关联的联系人、群组和消息
    contacts = relationship("Contact", back_populates="wechat_account")
    groups = relationship("Group", back_populates="wechat_account")
    messages = relationship("Message", back_populates="wechat_account")
    
    def __repr__(self):
        return f"<WechatAccount(wxid='{self.wxid}', nickname='{self.nickname}')>"

class Contact(Base):
    """联系人表，存储微信联系人信息"""
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    wxid = Column(String(100), index=True, nullable=False)  # 微信ID
    nickname = Column(String(100), nullable=True)  # 昵称
    remark = Column(String(100), nullable=True)  # 备注名
    avatar_url = Column(String(255), nullable=True)  # 头像URL
    contact_type = Column(Integer, default=1)  # 联系人类型：1-个人，2-群组，3-公众号，4-其他
    is_in_contact_list = Column(Boolean, default=True)  # 是否在联系人列表中
    
    # 外键关联
    account_id = Column(Integer, ForeignKey("wechat_accounts.id"))
    wechat_account = relationship("WechatAccount", back_populates="contacts")
    
    # 注释掉所有复杂关系
    # messages = relationship(...)
    # media_files = relationship(...)
    
    def __repr__(self):
        return f"<Contact(wxid='{self.wxid}', nickname='{self.nickname}')>"

class Group(Base):
    """群组表，存储微信群组信息"""
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String(100), index=True, nullable=False)  # 群组ID
    name = Column(String(100), nullable=True)  # 群名称
    owner_wxid = Column(String(100), nullable=True)  # 群主wxid
    avatar_url = Column(String(255), nullable=True)  # 群头像URL
    member_count = Column(Integer, default=0)  # 成员数量
    
    # 外键关联
    account_id = Column(Integer, ForeignKey("wechat_accounts.id"))
    wechat_account = relationship("WechatAccount", back_populates="groups")
    
    # 群组成员和消息
    members = relationship("GroupMember", back_populates="group")
    
    def __repr__(self):
        return f"<Group(group_id='{self.group_id}', name='{self.name}')>"

class GroupMember(Base):
    """群成员表，存储群成员信息"""
    __tablename__ = "group_members"
    
    id = Column(Integer, primary_key=True, index=True)
    member_wxid = Column(String(100), nullable=False)  # 成员微信ID
    nickname = Column(String(100), nullable=True)  # 群内昵称
    
    # 外键关联
    group_id = Column(Integer, ForeignKey("groups.id"))
    group = relationship("Group", back_populates="members")
    
    # 账号ID（冗余存储，便于查询）
    account_id = Column(Integer, ForeignKey("wechat_accounts.id"))
    
    def __repr__(self):
        return f"<GroupMember(group_id='{self.group_id}', member_wxid='{self.member_wxid}')>"

class Message(Base):
    """消息表，存储聊天消息"""
    __tablename__ = "messages"
    
    id = Column(String(50), primary_key=True)
    app_id = Column(String(50), nullable=False)
    from_user = Column(String(50), nullable=False)  # 使用原始字段名
    to_user = Column(String(50), nullable=False)    # 使用原始字段名
    content = Column(Text, nullable=True)
    msg_type = Column(Integer, nullable=False)
    create_time = Column(DateTime, default=dt.now)
    raw_data = Column(Text, nullable=True)
    
    # 外键关联
    account_id = Column(Integer, ForeignKey("wechat_accounts.id"))
    wechat_account = relationship("WechatAccount", back_populates="messages")
    
    # 媒体文件
    media_files = relationship("MediaFile", back_populates="message")
    
    def to_dict(self):
        """转换为字典，用于API响应"""
        return {
            "id": self.id,
            "app_id": self.app_id,
            "sender": self.from_user,  # 在输出中使用新名称
            "receiver": self.to_user,  # 在输出中使用新名称
            "content": self.content,
            "msg_type": self.msg_type,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "type": "chat_message",
            "data": json.loads(self.raw_data) if self.raw_data else None
        }

class MediaFile(Base):
    """媒体文件表，存储消息中的媒体文件信息"""
    __tablename__ = "media_files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_type = Column(Integer, default=1)  # 文件类型：1-图片，2-视频，3-语音，4-文件
    file_url = Column(String(255), nullable=True)  # 文件URL
    thumb_url = Column(String(255), nullable=True)  # 缩略图URL
    aes_key = Column(String(100), nullable=True)  # AES密钥
    file_id = Column(String(255), nullable=True)  # 文件ID
    local_path = Column(String(255), nullable=True)  # 本地存储路径
    created_at = Column(DateTime, default=dt.utcnow)  # 创建时间
    
    # 外键关联 - 只与消息相关
    message_id = Column(Integer, ForeignKey("messages.id"))
    message = relationship("Message", back_populates="media_files")
    
    # 移除不存在的关系
    # contact = relationship(...)
    
    def __repr__(self):
        return f"<MediaFile(id='{self.id}', file_type='{self.file_type}')>" 