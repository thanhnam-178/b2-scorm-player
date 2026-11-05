FROM --platform=linux/amd64 python:3.12-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install --default-timeout=300 --retries=10 -r requirements.txt
COPY src ./src
ENV PYTHONPATH=/code/src
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]