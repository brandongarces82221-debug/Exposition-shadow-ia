FROM python:3.12-slim
RUN pip install --no-cache-dir pandas matplotlib boto3 \
 && useradd --create-home --uid 1001 ejecutor \
 && python -c "import matplotlib.pyplot"
ENV MPLCONFIGDIR=/tmp/mpl PYTHONUNBUFFERED=1
WORKDIR /app
COPY ejecutor.py servidor.py ./
# El servidor corre como root solo para poder lanzar el código como el usuario "ejecutor" (sin privilegios)
EXPOSE 8080
CMD ["python", "servidor.py"]
