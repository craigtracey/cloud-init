FROM ubuntu:xenial

RUN apt-get update -y && apt-get install -y build-essential python3-yaml python3-jsonpatch python3-configobj python3-jsonschema dh-systemd python3-contextlib2 python3-httpretty python3-nose python3-unittest2 python3-mock python3-coverage python3-oauthlib python3-jinja2 python3-requests devscripts git python3-pip

COPY . .
RUN pip3 install -r requirements.txt
ENV SKIP_UNCOMITTED_CHANGES_CHECK=1
RUN make deb

FROM centos:latest
RUN yum install -y epel-release
RUN yum install -y git python-pip make python-configobj python-oauthlib \
        	python-six \
        	PyYAML \
        	python-jsonpatch \
        	python-jinja2 \
        	python-jsonschema \
        	python-requests \
        	e2fsprogs \
        	iproute \
        	net-tools \
        	rsyslog \
        	sudo \
        	python-devel \
                rpm-build
COPY . .
RUN pip install -r requirements.txt
ENV SKIP_UNCOMITTED_CHANGES_CHECK=1
RUN make rpm
