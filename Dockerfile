FROM alpine:latest
RUN apk add --no-cache ca-certificates python3 gcc python3-dev libc-dev libffi libffi-dev openssl openssl-dev && mkdir -p /repo/netherappbot
ADD setup.py README.rst LICENSE setup.cfg /repo/
ADD netherappbot/*.py /repo/netherappbot/
RUN pip3 install /repo/ && rm -rf /repo && apk del gcc python3-dev libc-dev libffi-dev openssl-dev
CMD netherappbot
