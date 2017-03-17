#
# To build:
# > sudo docker build -t scrapyrt .
#
# to start as daemon with port 9080 of api exposed as 9080 on host
# and host's directory ${PROJECT_DIR} mounted as /scrapyrt/project
#
# > sudo docker run -p 9080:9080 -tid -v ${PROJECT_DIR}:/scrapyrt/project scrapyrt
#

FROM ubuntu:14.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && \
    apt-get install -y python python-dev  \
    libffi-dev libxml2-dev libxslt1-dev zlib1g-dev libssl-dev wget

RUN mkdir -p /scrapyrt/src /scrapyrt/project
RUN mkdir -p /var/log/scrapyrt

RUN wget "https://bootstrap.pypa.io/get-pip.py"
RUN python get-pip.py
RUN pip install scrapyrt

WORKDIR /scrapyrt/project

ENTRYPOINT ["scrapyrt", "-i 0.0.0.0"]

EXPOSE 9080
