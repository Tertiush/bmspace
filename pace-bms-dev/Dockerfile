FROM python:3.9-alpine

ENV WORK_DIR=workdir \
  HASSIO_DATA_PATH=/data

RUN mkdir -p ${WORK_DIR}
WORKDIR /${WORK_DIR}
COPY requirements.txt .

# install python libraries
RUN pip3 install -r requirements.txt

# Copy code
COPY bms.py constants.py run.sh ./
RUN chmod a+x run.sh

CMD [ "sh", "./run.sh" ]
