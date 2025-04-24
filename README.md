# fastapi-backend

```text
fastapi-backend/
    /ddl                // 数据库脚本
    /configs            // 配置文件
    /internal           // 内部模块
        /config         // 配置相关
        /constant       // 常量
        /controller     // 控制器，数据转换返回前端
        /dao            // 数据访问层实现
        /core           // 权限相关模块
        /schemas        // 实体
        /infra          // 基础设施层
        /middleware     // 中间件
        /models         // 数据库模型
        /service        // 服务层，主要业务逻辑
        /transformers   // 数据转换
        /utils          // 内部工具包
    /pkg                // 工具模块
    /proto              // proto文件
    /proto_generated    //proto生成的文件
    /scripts            // 脚本
    /main.go            // 入口文件，初始化
    /README.md          // 说明
    /uv.lock            // 依赖锁文件
    /pyprojecy.toml     // pip配置文件
    
    请求示例：
        前端 -- > middleware -- > controller -- > service -- > dao -- > service -- > controller --> transformers --> 前端
```

```shell
初始化环境 uv venv .venv && uv pip sync uv.lock

激活环境  source .venv/bin/activate

添加新依赖 uv pip add <包名> --dev

更新锁文件 uv pip compile --output uv.lock

重建环境   rm -rf .venv && uv pip sync uv.lock

```