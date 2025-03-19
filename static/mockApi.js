/**
 * 模拟API助手，用于前端开发和测试
 */
const MockApi = {
    // 存储状态
    state: {
        loggedIn: false,
        qrCodeGenerated: false,
        qrCodeScanned: false,
        token: null,
        loginConfirmed: false,
        contacts: []
    },
    
    // 重置状态
    reset() {
        this.state = {
            loggedIn: false,
            qrCodeGenerated: false,
            qrCodeScanned: false,
            token: null,
            loginConfirmed: false,
            contacts: []
        };
    },
    
    // 模拟授权登录
    async mockAuthLogin(authCode) {
        return new Promise(resolve => {
            setTimeout(() => {
                if (authCode === 'your-secret-auth-code') {
                    this.state.token = 'mock-token-' + Date.now();
                    resolve({
                        status: 'success',
                        token: this.state.token
                    });
                } else {
                    resolve({
                        status: 'error',
                        message: '授权码无效'
                    });
                }
            }, 500);
        });
    },
    
    // 模拟获取二维码
    async mockGetQRCode() {
        return new Promise(resolve => {
            setTimeout(() => {
                // 使用在线二维码生成服务
                const qrData = `https://example.com/login?t=${Date.now()}`;
                const qrImageUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(qrData)}`;
                
                this.state.qrCodeGenerated = true;
                this.state.qrCodeScanned = false;
                this.state.loginConfirmed = false;
                
                resolve({
                    ret: 200,
                    msg: "操作成功",
                    data: {
                        qrData: qrData,
                        qrImgBase64: qrImageUrl,
                        uuid: "mock-uuid-" + Date.now(),
                        appId: "mock-appid"
                    }
                });
            }, 1000);
        });
    },
    
    // 模拟检查登录状态
    async mockCheckLoginStatus() {
        return new Promise(resolve => {
            setTimeout(() => {
                let status = 0;
                
                if (!this.state.qrCodeGenerated) {
                    resolve({
                        status: 'error',
                        message: '请先获取登录二维码'
                    });
                    return;
                }
                
                // 随机模拟扫码状态变化
                if (!this.state.qrCodeScanned) {
                    // 有20%的概率扫码
                    if (Math.random() < 0.2) {
                        this.state.qrCodeScanned = true;
                    }
                } else if (!this.state.loginConfirmed) {
                    // 已扫码，有30%的概率确认登录
                    if (Math.random() < 0.3) {
                        this.state.loginConfirmed = true;
                        this.state.loggedIn = true;
                    }
                }
                
                if (this.state.loginConfirmed) {
                    status = 2; // 已确认登录
                } else if (this.state.qrCodeScanned) {
                    status = 1; // 已扫码，等待确认
                } else {
                    status = 0; // 等待扫码
                }
                
                resolve({
                    ret: 200,
                    msg: "操作成功",
                    data: {
                        uuid: "mock-uuid",
                        headImgUrl: null,
                        nickName: status === 2 ? "模拟用户" : null,
                        expiredTime: 300 - Math.floor(Math.random() * 100),
                        status: status,
                        loginInfo: status === 2 ? {
                            uin: 12345678,
                            wxid: "wxid_mock123",
                            nickName: "模拟用户",
                            mobile: "13800138000",
                            alias: "mock_user"
                        } : null
                    }
                });
            }, 500);
        });
    },
    
    // 模拟获取联系人列表
    async mockGetContacts() {
        return new Promise(resolve => {
            setTimeout(() => {
                if (!this.state.loggedIn) {
                    resolve({
                        status: 'error',
                        message: '用户未登录'
                    });
                    return;
                }
                
                // 如果还没有生成联系人，生成一些模拟数据
                if (this.state.contacts.length === 0) {
                    const names = ['张三', '李四', '王五', '赵六', '钱七', '孙八', '周九', '吴十'];
                    const groups = ['家人群', '同学群', '工作群', '兴趣小组'];
                    
                    // 生成个人联系人
                    for (let i = 0; i < 8; i++) {
                        this.state.contacts.push({
                            wxid: `wxid_${i}${Date.now()}`,
                            nickname: names[i],
                            remark: Math.random() > 0.5 ? `备注-${names[i]}` : '',
                            type: 1, // 个人
                            lastMessage: `你好，我是${names[i]}，最近在忙什么？`,
                            lastTime: new Date(Date.now() - Math.random() * 86400000).toISOString()
                        });
                    }
                    
                    // 生成群组
                    for (let i = 0; i < 4; i++) {
                        this.state.contacts.push({
                            wxid: `group_${i}${Date.now()}`,
                            nickname: groups[i],
                            remark: '',
                            type: 2, // 群组
                            lastMessage: `[${names[Math.floor(Math.random() * names.length)]}]: 群里有人在吗？`,
                            lastTime: new Date(Date.now() - Math.random() * 86400000).toISOString()
                        });
                    }
                }
                
                resolve({
                    status: 'success',
                    contacts: this.state.contacts
                });
            }, 800);
        });
    },
    
    // 模拟发送消息
    async mockSendMessage(toWxid, content) {
        return new Promise(resolve => {
            setTimeout(() => {
                if (!this.state.loggedIn) {
                    resolve({
                        status: 'error',
                        message: '用户未登录'
                    });
                    return;
                }
                
                // 更新联系人的最新消息
                const contact = this.state.contacts.find(c => c.wxid === toWxid);
                if (contact) {
                    contact.lastMessage = content;
                    contact.lastTime = new Date().toISOString();
                }
                
                resolve({
                    status: 'success',
                    message: '消息发送成功',
                    data: {
                        msgId: 'mock-msgid-' + Date.now(),
                        timestamp: Date.now()
                    }
                });
            }, 300);
        });
    }
};

// 如果在浏览器环境，将MockApi附加到全局对象
if (typeof window !== 'undefined') {
    window.MockApi = MockApi;
}

// 如果是Node.js环境，导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MockApi;
} 