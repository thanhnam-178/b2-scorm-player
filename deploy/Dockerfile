FROM python:3.12-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src ./src
ENV PYTHONPATH=/code/src
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]