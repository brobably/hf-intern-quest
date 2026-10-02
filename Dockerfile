FROM python:3.12-slim
WORKDIR /app
COPY server.py /app/server.py
COPY dist /app/dist
ENV HF_BIND=0.0.0.0 HF_DATA=/var/data HF_HTTPS=1 PYTHONUNBUFFERED=1
EXPOSE 10000
CMD ["python", "server.py"]
