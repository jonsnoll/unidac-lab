FROM --platform=linux/386 i386/ubuntu:14.04

ENV DEBIAN_FRONTEND=noninteractive

COPY .libssl1.0.0_1.0.1f-1ubuntu9.8_i386.deb /tmp/libssl.deb

RUN set -eux; \
    dpkg -i /tmp/libssl.deb; \
    LIBCRYPTO="$(dpkg -L libssl1.0.0 | grep '/libcrypto\.so\.1\.0\.0$' | head -n 1)"; \
    test -n "$LIBCRYPTO"; \
    ln -sf "$LIBCRYPTO" /usr/lib/libcrypto.so.4; \
    ldconfig; \
    test -e /usr/lib/libcrypto.so.4; \
    rm -f /tmp/libssl.deb

COPY readiness.sh /usr/local/bin/iol-readiness

RUN chmod 0755 /usr/local/bin/iol-readiness

ENTRYPOINT ["/usr/local/bin/iol-readiness"]
