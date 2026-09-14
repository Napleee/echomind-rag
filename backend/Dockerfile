# EchoMind 后端镜像（Python 3.12）
FROM python:3.12-slim

# 日志实时输出；不生成 .pyc
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# HuggingFace 国内镜像（容器内首次启动下载 embedding 模型用）
ENV HF_ENDPOINT=https://hf-mirror.com

WORKDIR /app

# 先只复制依赖清单：利用 Docker 层缓存，代码改动不会触发依赖重装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 国内构建加速写法（用下面这行替换上一行 RUN）:
# RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 再复制应用代码
COPY app/ ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
