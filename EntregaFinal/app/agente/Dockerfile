FROM python:3.12-slim
RUN pip install --no-cache-dir "anthropic[bedrock]>=1.17,<2" boto3 \
 && useradd --create-home --uid 1001 agente
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY agente.py almacen.py servidor_agente.py ./
USER agente
EXPOSE 8080
CMD ["python", "servidor_agente.py"]
