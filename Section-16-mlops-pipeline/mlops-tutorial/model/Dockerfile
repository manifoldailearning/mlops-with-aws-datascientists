ARG REGION

FROM 763104351884.dkr.ecr.${REGION}.amazonaws.com/tensorflow-training:2.6.0-cpu-py38-ubuntu20.04-v1.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -U \
    flask \
    gevent \
    gunicorn

RUN mkdir -p /opt/program
RUN mkdir -p /opt/ml

COPY app.py /opt/program
COPY model.py /opt/program
COPY nginx.conf /opt/program
COPY wsgi.py /opt/program
WORKDIR /opt/program

EXPOSE 8080

ENTRYPOINT ["python", "app.py"]