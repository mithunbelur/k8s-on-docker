# Add a target to the Makefile for building the Docker image
# This target will build the Docker image for the http-udp-server
# The image will be tagged as "http-udp-server:latest"
# and pushed to the local Docker registry at 127.0.0.1:5000

all:
	docker build -t 127.0.0.1:5000/http-udp-server:latest .
	docker push 127.0.0.1:5000/http-udp-server:latest