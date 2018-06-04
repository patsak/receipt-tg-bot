# tg-receipt-bot

Бот для telegram для извлечения полного содержимого чека по тексту из баркода и запись его в google spreadsheet.  

![Alt text](/blob/barcode.png?raw=true "Barcode")
![Alt text](/blob/spreadsheet.png?raw=true "Google spreadsheet")

Запущенная версия бота - https://t.me/ReceiptDecodeBot  

## Запуск
```
$ cat << EOF > nginx.env
NGINX_HOST=bot.example.com # host where bot has been started
TOKEN=104367746AbAbAbAbAbAbAbAb-yZw # telegram bot token
EOF

$ cat << EOF | tee web-auth.env > bot.env
CLIENT_SECRET=hjeuUHjsdhueh2 # Google OAuth2 client secret from here https://console.developers.google.com
CLIENT_ID=898923489-daskjkjkjkds12jk.apps.googleusercontent.com # Google OAuth2 client id from here https://console.developers.google.com
TOKEN=104367746AbAbAbAbAbAbAbAb-yZw # telegram bot token
DEBUG=True # log level
REDIRECT_URI=https://bot.example.com/auth # google oauth2 redirect url
WEBHOOK_BASE_URL=https://bot.example.com # base url for telegram webhook. Must be https. 
REDIS_HOST=redis

$ docker-compose up

```
