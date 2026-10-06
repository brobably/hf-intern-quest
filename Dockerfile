FROM python:3.12-slim
WORKDIR /app
COPY server.py /app/server.py
COPY storage.py activity.py meals.py wiki.py news.py requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY dist /app/dist
ENV HF_BIND=0.0.0.0 HF_DATA=/var/data HF_HTTPS=1 PYTHONUNBUFFERED=1
EXPOSE 10000
CMD ["python", "server.py"]
