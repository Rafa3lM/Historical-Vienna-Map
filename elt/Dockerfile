FROM python:3.11-slim

WORKDIR /app

COPY elt/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY elt/ ./elt/
COPY data/ ./data/

CMD ["python", "-m", "elt.pipeline"]