FROM python:3.12.3-slim

# 设置工作目录
WORKDIR /app

# 先复制 requirements.txt 单独装依赖（利用 Docker 缓存）
COPY requirements.txt .

# 升级 pip 并安装依赖
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY . .

# Render 会通过 $PORT 环境变量传入端口
ENV PORT=8000

# 启动命令
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]