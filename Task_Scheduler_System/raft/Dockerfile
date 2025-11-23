FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir --default-timeout=100 grpcio==1.66.1 grpcio-tools==1.66.1

CMD ["python", "-u", "raft_node.py"]
