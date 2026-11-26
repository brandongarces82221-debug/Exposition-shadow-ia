FROM python:3.12-slim
RUN pip install --no-cache-dir pandas matplotlib boto3 \
 && for i in 1 2 3 4; do useradd --no-create-home --uid 100$i ejecutor$i; done
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY ejecutor.py servidor.py ./
# El servidor corre como root solo para lanzar cada ejecución con un usuario sin privilegios (ejecutor1..4)
EXPOSE 8080
CMD ["python", "servidor.py"]
