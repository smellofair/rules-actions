FROM alpine:3.10

RUN apk update
RUN apk add git openssh

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
