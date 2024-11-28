# 使用 Python 3.12.5 作为基础镜像
FROM python:3.12.5

# 设置工作目录
WORKDIR /app

# 设置阿里云的镜像源，如果 /root/.pip/pip.conf 不存在，则创建
RUN mkdir -p /root/.pip && \
    [ ! -f /root/.pip/pip.conf ] && \
    printf "[global]\nindex-url = https://mirrors.aliyun.com/pypi/simple/" > /root/.pip/pip.conf || true

# 升级 pip 到最新版本
RUN pip install --no-cache-dir --upgrade pip

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码到容器
COPY . .

# 暴露 FastAPI 服务端口
EXPOSE 28090

# 运行 FastAPI 应用
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "28090", "--workers", "4", "--loop", "uvloop", "--http", "httptools", "--access-log"]