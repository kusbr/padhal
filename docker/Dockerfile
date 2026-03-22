FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY src /app/src

EXPOSE 8000

CMD ["python3", "src/padhal_api.py"]
