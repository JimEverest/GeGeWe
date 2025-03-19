// 创建一个新的JavaScript文件，用于长轮询功能
class MessagePoller {
    constructor() {
        this.lastMsgId = null;
        this.lastMsgTime = null; // 添加时间戳字段
        this.userId = null;
        this.isPolling = false;
        this.messageHandlers = [];
        this.reconnectDelay = 3000; // 重连延迟（毫秒）
        this.maxReconnectDelay = 30000; // 最大重连延迟
        this.currentReconnectDelay = this.reconnectDelay;
        this._periodicPollingInterval = null;
    }

    // 设置用户ID
    setUserId(userId) {
        this.userId = userId;
        console.log(`设置用户ID: ${userId}`);
    }

    // 设置最后接收的消息ID
    setLastMsgId(msgId, msgTime) {
        if (msgId) {
            this.lastMsgId = msgId;
            if (msgTime) {
                this.lastMsgTime = msgTime;
                console.log(`设置最后消息: ID=${msgId}, 时间=${msgTime}`);
            } else {
                console.log(`设置最后消息ID: ${msgId}`);
            }
        }
    }

    // 添加消息处理器
    onMessage(handler) {
        if (typeof handler === 'function') {
            this.messageHandlers.push(handler);
        }
    }

    // 开始轮询
    startPolling() {
        if (this.isPolling) {
            console.log('轮询已在进行中');
            return;
        }

        this.isPolling = true;
        this.poll();
        console.log('开始长轮询');
    }

    // 停止轮询
    stopPolling() {
        this.isPolling = false;
        console.log('停止长轮询');
    }

    // 执行轮询
    async poll() {
        if (!this.isPolling) {
            console.log('轮询已停止，不再发送请求');
            return;
        }

        console.log(`开始轮询请求: lastMsgId=${this.lastMsgId}, userId=${this.userId}`);
        
        try {
            // 构建请求URL
            let url = `/api/messages/poll`;
            const params = new URLSearchParams();
            if (this.lastMsgId) {
                params.append('last_msg_id', this.lastMsgId);
            }
            if (this.userId) {
                params.append('user_id', this.userId);
            }
            
            if (params.toString()) {
                url += `?${params.toString()}`;
            }
            
            console.log(`发送轮询请求: ${url}`);
            
            // 发送长轮询请求
            const response = await fetch(url);
            
            console.log(`轮询响应状态: ${response.status}`);
            
            if (!response.ok) {
                throw new Error(`HTTP错误: ${response.status}`);
            }

            const data = await response.json();
            console.log('轮询响应数据:', data);

            // 处理接收到的消息
            if (data.messages && data.messages.length > 0) {
                console.log(`收到 ${data.messages.length} 条新消息`);
                
                // 更新最后接收的消息ID
                const lastMessage = data.messages[data.messages.length - 1];
                if (lastMessage.id) {
                    this.lastMsgId = lastMessage.id;
                    console.log(`更新最后消息ID: ${this.lastMsgId}`);
                }

                // 调用所有消息处理器
                for (const handler of this.messageHandlers) {
                    try {
                        handler(data.messages);
                    } catch (error) {
                        console.error('消息处理器错误:', error);
                    }
                }
            } else {
                console.log('没有新消息');
            }

            // 重置重连延迟
            this.currentReconnectDelay = this.reconnectDelay;
            
            // 立即开始下一次轮询
            this.poll();
        } catch (error) {
            console.error('轮询出错:', error);
            
            // 增加重连延迟（指数退避）
            this.currentReconnectDelay = Math.min(
                this.currentReconnectDelay * 1.5, 
                this.maxReconnectDelay
            );
            
            console.log(`将在 ${this.currentReconnectDelay/1000} 秒后重试...`);
            
            // 延迟后重试
            setTimeout(() => {
                if (this.isPolling) {
                    this.poll();
                }
            }, this.currentReconnectDelay);
        }
    }

    // 添加定时轮询方法
    startPeriodicPolling() {
        if (this._periodicPollingInterval) {
            console.log('定时轮询已在进行中');
            return;
        }
        
        console.log('开始定时轮询，间隔: 3秒');
        
        // 立即执行一次
        this.fetchMessages();
        
        // 设置定时器
        this._periodicPollingInterval = setInterval(() => {
            this.fetchMessages();
        }, 3000);
    }

    // 停止定时轮询
    stopPeriodicPolling() {
        if (this._periodicPollingInterval) {
            clearInterval(this._periodicPollingInterval);
            this._periodicPollingInterval = null;
            console.log('停止定时轮询');
        }
    }

    // 获取消息
    async fetchMessages() {
        console.log(`获取消息: lastMsgId=${this.lastMsgId}, userId=${this.userId}`);
        
        try {
            // 构建请求URL
            let url = `/api/messages/fetch`;
            const params = new URLSearchParams();
            
            if (this.lastMsgId) {
                params.append('last_msg_id', this.lastMsgId);
                console.log(`使用last_msg_id=${this.lastMsgId}查询新消息`);
            }
            
            if (this.userId) {
                params.append('user_id', this.userId);
            }
            
            if (params.toString()) {
                url += `?${params.toString()}`;
            }
            
            console.log(`发送请求: ${url}`);
            
            // 发送请求
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP错误: ${response.status}`);
            }

            const data = await response.json();
            console.log('收到响应:', data);
            
            // 处理接收到的消息
            if (data.messages && data.messages.length > 0) {
                console.log(`收到 ${data.messages.length} 条新消息:`, data.messages);
                
                // 更新最后接收的消息ID和时间
                const lastMessage = data.messages[data.messages.length - 1];
                if (lastMessage.id) {
                    console.log(`更新lastMsgId: ${this.lastMsgId} -> ${lastMessage.id}`);
                    this.lastMsgId = lastMessage.id;
                    if (lastMessage.create_time) {
                        this.lastMsgTime = lastMessage.create_time;
                    }
                }

                // 调用所有消息处理器
                for (const handler of this.messageHandlers) {
                    try {
                        handler(data.messages);
                    } catch (error) {
                        console.error('消息处理器错误:', error);
                    }
                }
            } else {
                console.log('没有新消息');
            }
        } catch (error) {
            console.error('获取消息出错:', error);
        }
    }
}

// 创建全局轮询器实例
const messagePoller = new MessagePoller(); 