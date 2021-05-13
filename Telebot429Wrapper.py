import time
import telebot
import logging


class Telebot429Wrapper(telebot.TeleBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def wrapper429(self, method, args, kwargs):
        while True:
            try:
                result = method(*args, **kwargs)
                return result
            except telebot.apihelper.ApiTelegramException as e:
                if e.result_json['error_code'] == 429:
                    wait_seconds = e.result_json.get("parameters", {}).get("retry_after", 60)
                    logging.warning(f"Received 429 Too Many Errors from Telegram: waiting for {wait_seconds} seconds.")
                    time.sleep(wait_seconds)
                else:
                    raise

    def send_message(self, *args, **kwargs):
        self.wrapper429(super().send_message, args, kwargs)

    def send_media_group(self, *args, **kwargs):
        self.wrapper429(super().send_media_group, args, kwargs)
