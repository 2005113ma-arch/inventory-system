# 使用官方轻量级 Python 镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /code

# 将依赖文件复制到容器中
COPY ./requirements.txt /code/requirements.txt

# 安装 Python 依赖（使用阿里云镜像加速下载）
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 将项目代码复制到容器中
COPY ./app /code/app
COPY ./.env /code/.env

# 暴露 FastAPI 默认运行端口
EXPOSE 8000

# 启动 FastAPI 服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]