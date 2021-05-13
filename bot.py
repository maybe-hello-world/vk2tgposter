# -*- coding: utf-8 -*-

import os
import time
from typing import Optional, List

import requests
import logging
import telebot

import config
from Telebot429Wrapper import Telebot429Wrapper


class VK2TGPoster:
    def __init__(self):
        if config.owner is None and config.domain is None:
            raise ValueError("Either owner (number) or domain (short name) should be presented")

        if config.use_proxy:
            self.__init_proxy()

        # Create URL from domain/owner
        self.URL_VK = config.URL_VK.format(config.count, config.vk_access_token, config.v)
        if config.domain is not None:
            self.URL_VK += f"&domain={config.domain}"
        else:
            self.URL_VK += f"&owner_id={config.owner}"

        self.bot = Telebot429Wrapper(config.telegram_bot_token)
        self.__check_or_create_last_id()

    @staticmethod
    def try_parse_int(value: str) -> Optional[int]:
        """
        Tries to parse int from given str input
        :param value: possible integer number represented as string
        :return: Number is successfully parsed, None otherwise
        """
        try:
            return int(value)
        except ValueError:
            return None

    def __check_or_create_last_id(self):
        if not (os.path.exists(config.lastid_file)):
            data = self.get_data()
            if data is None:
                raise ValueError("Last_id is not provided and couldn't receive a news feed to extract last_id."
                                 " Exiting...")
            data = data.get("response", {}).get("items", [{'id': 0}])
            max_id = max(x.get('id', 0) for x in data)
            if max_id == 0:
                logging.warning("max_id parsed from the news feed is 0. Possibly there are no any posts yet, "
                                "but it is better to check.")
            logging.info("Last_id was not found, "
                         f"posting the last post and setting the last post id as max_id = {max_id}")
            self.__update_last_id(max_id-1)

        self.__get_last_id()

    def __get_last_id(self) -> int:
        """
        Extract last id from the last_known_id file
        :returns: parsed last_id number
        """

        with open(config.lastid_file, 'rt') as idfile:
            last_id = idfile.read().strip()
            last_id = self.try_parse_int(last_id)
            if last_id is None:
                raise ValueError('Could not parse the last number from last_id file.')
            logging.debug(f'Last VK post ID read = {last_id}.')
            return last_id

    @staticmethod
    def __init_proxy() -> None:
        """
        Initialize proxy settings if needed
        """
        telebot.apihelper.proxy = {'https': 'socks5://{}:{}@{}:{}'.format(
            config.proxy_user,
            config.proxy_pass,
            config.proxy_address,
            config.proxy_port
        )}
        logging.info("Proxy initialized.")

    @staticmethod
    def __update_last_id(last_id: int) -> None:
        # write last id to file
        with open(config.lastid_file, 'wt') as idfile:
            idfile.write(str(last_id))
            logging.debug(f'New VK post last_id is {last_id}')

    def get_data(self) -> Optional[dict]:
        """
        Receive data from VK
        :return: None if nothing received, dict with data otherwise
        """
        try:
            result = requests.get(self.URL_VK, timeout=10).json()
            if 'error' in result:
                raise ValueError(result)
            return result
        except requests.exceptions.Timeout:
            logging.warning("Got Timeout while retrieving VK JSON data. Cancelling...")
            return None

    # check posts
    def check_new_posts_vk(self):
        logging.debug('Started looking for new posts...')

        # find last id
        last_id = self.__get_last_id()

        # receive news feed
        feed = self.get_data()
        logging.debug("Data received.")
        if feed is None:
            logging.warning('Received feed is None! Skipping the step...')
            return

        entries = feed.get("response", {}).get("items", [])
        if not entries:
            logging.warning("feed.response.items is empty.")

        # delete all posts that already were published
        entries = [x for x in entries if x.get('id', 0) > last_id]
        if entries:
            self.send_new_posts(entries)
        else:
            logging.debug("No new posts are available.")

        logging.debug("New posts received and reposted.")
        return

    def send_new_posts(self, items: List[dict]) -> None:
        """
        Send all received items to the channel
        :param items: list of entries
        """

        # first post in the list is the last one
        items = reversed(items)

        for item in items:

            # Posts without text?
            message = f"{item['text']}\n" if 'text' in item else "<bot>: no text in original message\n"
            media_group = []

            # list attachments
            if 'attachments' in item:
                attachments = {
                    "photo": [],
                    "link": [],
                    "other": set()
                }

                for attachment in item['attachments']:
                    # Get photos, links, and types of other attachments
                    if attachment['type'] == "photo":
                        # find biggest size for image
                        biggest_photo = max(attachment["photo"]["sizes"], key=lambda x: x["width"])["url"]
                        attachments['photo'].append(biggest_photo)
                    elif attachment['type'] == "link":
                        attachments["link"].append(attachment['link']['url'])
                    else:
                        attachments['other'].add(attachment['type'])

                # Photos are sent in next message as album
                if attachments['photo']:
                    for i in attachments['photo']:
                        media_group.append(telebot.types.InputMediaPhoto(i))

                if attachments['link']:
                    message += "\nLinks:\n"
                    message += "\n".join(attachments['link']) + "\n"

                # Say that there are other types of attachments in post
                if attachments['other']:
                    message += f"There are another attachments with types: {','.join(attachments['other'])}\n"

            # add link to original message and send
            message += f"\nOriginal URL: {config.BASE_POST_URL}{item.get('id', '')}"
            split_message = telebot.util.split_string(message, 4000)

            # First message is sent with notification, all others - without
            notif_disabled = False
            for text in split_message:
                self.bot.send_message(config.channel_name, text, disable_notification=notif_disabled)
                notif_disabled = True

            # if media_group send will fail, we will not retry it
            self.__update_last_id(item["id"])
            time.sleep(1)

            # send photos as albums
            if media_group:
                self.bot.send_media_group(config.channel_name, media_group, disable_notification=True)

            time.sleep(5)
        return

    def run(self):
        while True:
            try:
                self.check_new_posts_vk()
                logging.debug(f"Sleeping for timeout = {config.check_timeout} seconds.")
                time.sleep(config.check_timeout)
            except Exception as e:
                logging.exception(e)
                logging.error("Exception raised. Notifying the service channel and sleeping for 5x timeout == "
                              f"{5 * config.check_timeout}")

                # notification to the service channel
                try:
                    self.bot.send_message(config.service_channel_name, str(e))
                except Exception as e:
                    logging.exception(e)
                    logging.error("Received the exception during handling the exception. "
                                  "Possibly 429 from Telegram, go on sleeping...")

                time.sleep(5 * config.check_timeout)
            except BaseException as e:
                logging.info(f"Bot stopped due to {str(e)}")
                return


if __name__ == "__main__":
    # set requests logging level to CRITICAL only
    logging.getLogger('requests').setLevel(logging.CRITICAL)

    log_level = config.log_level
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR
    }
    log_level = levels.get(log_level, logging.DEBUG)

    logging.basicConfig(
        format='[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s',
        level=log_level,
        datefmt='%d.%m.%Y %H:%M:%S'
    )

    vk2tgposter = VK2TGPoster()
    vk2tgposter.run()
    logging.info('Script exited.\n')
