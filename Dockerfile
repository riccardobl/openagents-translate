FROM python:3.11.9-slim
ADD src /app
ADD requirements.txt /app
WORKDIR /app
RUN pip install 'transformers[torch]'
RUN pip install -r requirements.txt

ENV NOSTR_CONNECT_GRPC_BINDING_ADDRESS="127.0.0.1"
ENV NOSTR_CONNECT_GRPC_BINDING_PORT="5000"
ENV DEVICE="-1"

CMD ["python", "main.py"]
