FROM python:3.12-slim

WORKDIR /srv/breakthrough

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY tests ./tests
COPY run.py pytest.ini ./

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# 服务固定运行在 8080 端口
CMD ["python", "run.py"]
