"""

pip install uvicorn

# 推荐启动方式 main指当前文件名字 app指FastAPI对象名称
uvicorn main:app --host=127.0.0.1 --port=8010 --reload


类似flask 工厂模式创建


# 生产启动命令 去掉热重载 (可用supervisor托管后台运行)
在main.py同文件下下启动
uvicorn main:app --host=127.0.0.1 --port=8010 --workers=4

# 同样可以也可以配合gunicorn多进程启动  main.py同文件下下启动 默认127.0.0.1:8000端口
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8020

"""
from apps import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app='main:app', host="0.0.0.0", port=8081, reload=True, debug=True)