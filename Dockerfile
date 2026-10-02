FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV HOST=0.0.0.0
ENV PORT=7860
ENV OPEN_BROWSER=0
EXPOSE 7860

CMD ["python", "app.py"]

