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

RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 627220E7
RUN echo 'deb http://archive.scrapy.org/ubuntu scrapy main' | tee /etc/apt/sources.list.d/scrapy.list

RUN apt-get update && \
    apt-get install -y python python-dev python-pip \
    libffi-dev libxml2-dev libxslt1-dev zlib1g-dev libssl-dev

RUN mkdir -p /scrapyrt/src /scrapyrt/project
RUN mkdir -p /var/log/scrapyrt

WORKDIR /scrapyrt/src

ADD requirements.txt /scrapyrt/src/requirements.txt
RUN pip install -r requirements.txt

ADD . /scrapyrt/src
RUN pip install /scrapyrt/src

WORKDIR /scrapyrt/project

ENTRYPOINT ["scrapyrt"]

EXPOSE 9080
