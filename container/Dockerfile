# Copyright 2019 Wirepas Ltd

FROM python:3.7

RUN apt-get update;\
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        default-libmysqlclient-dev \
    && apt-get clean all \
    && rm -rf /var/lib/apt/lists/*

ENV SETTINGS_PATH=${SETTINGS_PATH:-"/home/wirepas/vars"}
WORKDIR /home/wirepas

# For caching purposes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install .

CMD wm-gw-cli --settings ${SETTINGS_PATH}

RUN mkdir -p ${SETTINGS_PATH} && cp examples/settings.yml ${SETTINGS_PATH}/settings.yml
ENV PYTHONUNBUFFERED=true
