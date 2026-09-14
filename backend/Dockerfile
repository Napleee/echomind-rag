# EchoMind 后端镜像（Python 3.12）
FROM python:3.12-slim

# 日志实时输出；不生成 .pyc
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# HuggingFace 国内镜像（容器内首次启动下载 embedding 模型用）
ENV HF_ENDPOINT=https://hf-mirror.com
# 模型缓存指向 /models（compose 挂命名卷持久化，重建容器不重复下载）
ENV HF_HOME=/models

WORKDIR /app

# 先只复制依赖清单：利用 Docker 层缓存，代码改动不会触发依赖重装
COPY requirements.txt .
# 先单独装 CPU 版 torch: 默认源会拉下带 CUDA 的巨型包（好几 GB），CPU 轮子不到 200MB
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch>=2.3" \
    && pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 再复制应用代码
COPY app/ ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
