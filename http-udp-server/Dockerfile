FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY main.go .

RUN go build -o server main.go

# Final image
FROM alpine:latest

# Install requested packages
RUN apk add --no-cache \
    bash \
    bash-completion \
    vim \
    curl \
    bind-tools \
    net-tools \
    sudo \
    tcpdump \
    iproute2 \
    iputils

# Copy the built Go app
COPY --from=builder /app/server .

# Expose HTTP and UDP ports
EXPOSE 8080 9090/udp

# Default command
CMD ["./server"]
