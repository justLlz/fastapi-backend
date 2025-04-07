fastapi-backend/
    /configs    // 配置文件
    /internal   // 内部模块
        /controller     // 控制器，数据转换返回前端
        /converter      // 转换器
        /dao            // 数据访问层
        /core           // 权限相关模块
        /dao            // 数据访问层实现
        /entity         // 实体
        /infra          // 基础设施层
        /middleware     // 中间件
        /models         // 数据库模型
        /router         // 路由
        /service        // 服务层，主要业务逻辑
        /utils          // 内部工具包
    /pkg        // 工具模块
    /scripts    // 脚本
    /main.go    // 入口文件，初始化
    
    请求示例：
        前端请求 -- > 中间件 -- > 控制器 -- > 服务层 -- > 数据访问层 -- > 数据库(model) -- > 控制器(返回entity) --> 响应 --> 前端
    