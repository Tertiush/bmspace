#ARG BUILD_FROM
#FROM $BUILD_FROM
FROM python:3.9-alpine

ENV WORK_DIR=workdir \
  HASSIO_DATA_PATH=/data

COPY . ${WORK_DIR}

# Install requirements for add-on
RUN \
  apk add --no-cache \
    python3

# install python library
RUN cd ${WORK_DIR} \
  && pip3 install --no-cache-dir -r requirements.txt

# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "sh", "./run.sh" ]
