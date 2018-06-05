IMAGE_NAME := tg-receipt-bot

build:
	docker build -t $(IMAGE_NAME) .

register: build
	docker run -it $(IMAGE_NAME) python3.6 receipt.py

run:
	docker-compose up
