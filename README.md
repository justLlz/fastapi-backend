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
    /pyproject.toml     // pip配置文件
    
    请求示例：
        前端 -- > middleware -- > controller -- > service -- > dao -- > service -- > controller --> transformers --> 前端
```

```shell
迁移
uv add -r requirements.txt

显示所有可安装/已安装版本 
uv python list
 
显示已经安装的版本
uv python find
 
初始化环境
uv venv .venv --python 3.12.9

安装所有包
uv sync --locked

添加新依赖
uv add <包名>

同步新依赖
uv lock && uv sync

所有的依赖
uv pip list

清理缓存
uv clean

导出到requirements.txt
uv export --output-file requirements.txt
--output-file：指定输出文件路径。
--no-header（可选）：不写入 uv 的注释头信息。
--frozen（可选）：生成带哈希值的冻结格式。
--dev（可选）：包含开发依赖。

重建环境
rm -rf .venv && uv sync

激活环境
source .venv/bin/activate
```