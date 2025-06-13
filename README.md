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

---

## 1. **必填，不可为None**

```python
from pydantic import BaseModel, Field


class User(BaseModel):
    name: str = Field(..., description="用户名，必填且不可为None")
```

* `...` 表示**必填**
* `name=None` 会报错，`User()` 也报错。

---

## 2. **必填，可以为None**

```python
class User(BaseModel):
    name: str | None = Field(..., description="用户名，必填但可以为None")
    # 或 name: Optional[str] = Field(...)
```

* 必须传，且允许传`None`。

---

## 3. **可选（非必填），默认None，允许None**

```python
class User(BaseModel):
    name: str | None = Field(None, description="用户名，可选，默认None")
```

* 可不传，`name` 默认为None。

---

## 4. **可选（非必填），有默认值，且不允许None**

```python
class User(BaseModel):
    name: str = Field("lilinze", description="用户名，可选，默认'lilinze'，不可为None")
```

* 不传就是`"lilinze"`，但传`None`会报错。

---

## 5. **可选（非必填），有默认值，也允许None**

```python
class User(BaseModel):
    name: str | None = Field("lilinze", description="用户名，可选，默认'lilinze'，也可为None")
```

* 可不传（默认为"lilinze"），可传None。

---

## 6. **类型限制+Field约束（最全样例）**

```python
class User(BaseModel):
    # 必填字符串，长度1-32
    name: str = Field(..., min_length=1, max_length=32, description="必填用户名")
    # 可选，默认18，限定范围
    age: int = Field(18, ge=0, le=150, description="年龄")
    # 可选，默认None，允许None
    email: str | None = Field(None, description="邮箱，可为None")
```

---

## 7. **示例对照表**

| 需求          | 写法                         | 行为                    |                     |
|-------------|----------------------------|-----------------------|---------------------|
| 必填不可为None   | `name: str = Field(...)`   | 必须传，且不能为None          |                     |
| 必填可为None    | \`name: str                | None = Field(...)\`   | 必须传，且允许None         |
| 可选默认None    | \`name: str                | None = Field(None)\`  | 可不传，默认为None         |
| 可选有默认值      | `name: str = Field("abc")` | 可不传，默认"abc"，None非法    |                     |
| 可选有默认且可None | \`name: str                | None = Field("abc")\` | 可不传，默认"abc"，也可传None |

---

## 8. **小结&推荐实践**

* **只要是必填，Field里就写`...`**
* **可选时，Field里写默认值（None 或字符串）**
* **支持所有Field参数（min\_length、max\_length、ge、le、title、description等）**

---

### 例子

```python
class Product(BaseModel):
    id: int = Field(..., description="ID，必填")
    title: str = Field(..., min_length=1, max_length=50, description="标题")
    price: float = Field(0.0, ge=0, description="价格，非负，默认0")
    tag: str | None = Field(None, description="可选标签")
```

---

如需更多嵌套、数组、字典等复杂场景样例可以继续问！
