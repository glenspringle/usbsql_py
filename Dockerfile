FROM python:3.13-slim

ARG DEVELOPMENT
ENV DEVELOPMENT=$DEVELOPMENT

WORKDIR /pcc

# Install system dependencies (Debian apt uses the same package names as Ubuntu)
RUN apt-get update && apt-get install -y \
    udev \
    usbutils \
    && rm -rf /var/lib/apt/lists/*

COPY docker/99-pcc-hotplug.rules /etc/udev/rules.d/99-pcc-hotplug.rules

COPY pyproject.toml .
COPY pcc pcc

RUN mkdir -p build/
RUN pip install --no-cache-dir --upgrade .
RUN if [ "$DEVELOPMENT" = "true" ] ; then pip install --no-cache-dir .[dev] ; fi
RUN rm -rf build/

CMD ["bash"]
