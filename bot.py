# -*- coding: utf-8 -*-

import time
import requests
import logging
import telebot

import config

if config.use_proxy:
	from telebot import apihelper
	apihelper.proxy = {'https':'socks5://{}:{}@{}:{}'.format(
		config.proxy_user,
		config.proxy_pass,
		config.proxy_address,
		config.proxy_port
	)}

# config check
assert config.owner is not None or config.domain is not None, "Owner (number) or domain (short name) of community must be not None"

# Create URL from domain/owner
config.URL_VK = config.URL_VK.format(config.count, config.vk_access_token, config.v)
if config.domain is not None:
	config.URL_VK += "&domain=" + config.domain
else:
	config.URL_VK += "&owner=" + config.owner

# start bot
bot = telebot.TeleBot(config.telegram_bot_token)

# get data from vk
# TODO: add offset?
def get_data():
	try:
		feed = requests.get(config.URL_VK, timeout=10)
		assert feed.json() is not None, '[Error] Feed got from error is None'
		return feed.json()
	except requests.exceptions.Timeout:
		logging.warning("[VK] Got Timeout while retrieving VK JSON data. Cancelling...")
		return None

# send all got items to channel
def send_new_posts(items, last_id):
	for item in reversed(items):
		if item['id'] <= last_id:
			continue

		# Posts without text?
		text = "No text in message :D"
		if 'text' in item:
			text = item['text'] + "\n"

		message = text

		# list attachements
		if 'attachments' in item:
			attaches = {
				"photo": [],
				"link": [],
				"other": set()
			}

			for attach in item['attachments']:
				# Get photo links and only types of other attaches
				if attach['type'] == "photo":
					# fucking vk with fucking image sizes
					# find biggest size for image
					keys = [int(i[6:]) for i in attach['photo'].keys() if i[:5] == 'photo']
					keys = sorted(keys)
					attaches['photo'].append(attach['photo']['photo_' + str(keys[-1])])
				elif attach['type'] == "link":
					attaches["link"].append(attach['link']['url'])
				else:
					attaches['other'].add(attach['type'])

			# Append photos to message
			if len(attaches['photo']) > 0:
				message += "\nPhotos:\n"
				message += "\n".join(attaches['photo']) + "\n"

			if len(attaches['link']) > 0:
				message += "\nLinks:\n"
				message += "\n".join(attaches['link']) + "\n"

			# Say that there are other types of attachements in post
			if len(attaches['other']) > 0:
				message += "There're another attachments with types: " + ",".join(attaches['other']) + "\n"


		# add link to original message and send
		message += "\nOriginal URL: {}{}".format(config.BASE_POST_URL, item['id'])
		splitted_message = telebot.util.split_string(message, 3000)
		for text in splitted_message:
			bot.send_message(config.channel_name, text)
		time.sleep(1)
	return

# check posts
def check_new_posts_vk():
	logging.info('[VK] Started scanning new posts...')

	# find last id
	with open(config.lastid_file, 'rt') as idfile:
		last_id = int(idfile.read())
		if last_id is None:
			logging.error('[File system] Could not read from storage. Skip iteration...')
			return
		logging.info('[File system] Last VK post ID read = {}'.format(last_id))


	try:
		feed = get_data()
		if feed is not None:
			entries = feed['response']['items']

			# send new posts
			send_new_posts(entries, last_id)

			# write last id to file
			with open(config.lastid_file, 'wt') as idfile:

				# do not set pinned post as last
				if 'is_pinned' in entries[0]:
					del entries[0]

				if len(entries) == 0:
					logging.error('[Error] Entries is null!')
				else:
					idfile.write(str(entries[0]['id']))
					logging.info('[File system] New VK post last_id  is {}'.format(entries[0]['id']))

	except Exception as ex:
		logging.exception('[Exception] Exception of type {} in check_new_post(): {}'.format(type(ex).__name__, str(ex)))

	logging.info("[VK] Finished scanning")
	return

if __name__ == "__main__":
	# set requests logging level to CRITICAL only
	logging.getLogger('requests').setLevel(logging.CRITICAL)

	logging.basicConfig(
		format='[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s',
		level=logging.INFO,
		filename=config.bot_log_file,
		datefmt='%d.%m.%Y %H:%M:%S'
	)

	try:
		while True:
			check_new_posts_vk()

			logging.info("[App] Sleeping for timeout...")
			time.sleep(60 * config.check_timeout)
	except BaseException as ex:
		logging.info("[App] Script stopped due to: {}".format(str(ex)))
	finally:
		logging.info('[App] Script exited.\n')


