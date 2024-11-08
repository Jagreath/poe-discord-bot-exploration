"""
Simple bot to poll official poe twitter and staff and post it to a discord channel webhook.
"""

import time
from datetime import datetime
import json
import requests
import xmltodict
import html2markdown
import logging
import sys 
import twitter

ENV = 'dev'
CONFIG_FILE_URI = 'config.{0}.json'
SECRET_FILE_URI = 'secrets.json'
LOG_FILE_URI = '{0}.{1}.log'

logger = logging.getLogger()

def setupLogger():
	logger.setLevel(logging.DEBUG)
	lformatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
	
	console_handler = logging.StreamHandler()
	console_handler.setFormatter(lformatter)
	logger.addHandler(console_handler)

	file_handler = logging.FileHandler(LOG_FILE_URI.format(__name__, datetime.now().isoformat(timespec='hours')))
	file_handler.setFormatter(lformatter)
	logger.addHandler(file_handler)

def getConfigUri():
	return CONFIG_FILE_URI.format(ENV)

def getConfig():
	"""Get configuration object"""
	try:
		with open(getConfigUri(), 'r') as config_file:
			return json.load(config_file)
	except:
		raise

def saveConfig(config):
	"""Save configuration object"""
	try:
		with open(getConfigUri(), 'w') as config_file:
			json.dump(config, config_file)
	except:
		raise

def getSecrets():
	"""Get secrets object"""
	try:
		with open(SECRET_FILE_URI, 'r') as secret_file:
			return json.load(secret_file)
	except:
		raise

def setupTwitterApi(secrets):
	try:
		api = twitter.Api(consumer_key=secrets['consumer_key'], consumer_secret=secrets['consumer_secret'], access_token_key=secrets['access_token_key'], access_token_secret=secrets['access_token_secret'], tweet_mode='extended')
		api.VerifyCredentials()
		return api		
	except:
		raise

def getTweets(api, screen_name, last_id):
	logger.debug('Retrieve tweets for "' + screen_name + '" since ' + str(last_id))

	try:
		tl = api.GetUserTimeline(screen_name=screen_name, include_rts=True, exclude_replies=True,since_id=last_id)
		logger.debug('Found (' + str(len(tl)) + ') tweets')
		return tl
	except:
		raise

def buildJsonStringFromTweets(tweets):
	"""Build json string from twitter status"""

	for tweet in tweets:
		tweet.created_at = datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S %z %Y')

	embeds = []
	for tweet in sorted(tweets, key = lambda t : t.created_at):
		embed_obj = {
			'author': {
				'name': tweet.user.name,
				'url': 'https://www.twitter.com/' + tweet.user.screen_name + '/status/' + tweet.id_str,
				'icon_url': tweet.user.profile_image_url
			},
			'color': 2007537,
			'description': tweet.full_text,
			'footer': {
				"text" : tweet.created_at.strftime('%a, %d %b %Y %H:%M %Z')
			}
		}

		if hasattr(tweet, 'media') and tweet.media:
			for m in tweet.media:
				embed_obj['image'] = {
					'url': m.media_url
				}
				break

		embeds.append(embed_obj)

	try:
		return json.dumps({ 'embeds': embeds })
	except:
		logger.warning('Unable to create json string')
		raise

def postToHook(secrets, json_string):
	"""Post json string to hook uri"""
	logger.debug('Posting json to hook | ' + json_string)

	if secrets['hook_uri'].startswith('http'):

		try:
			response = requests.post(secrets['hook_uri'], data=json_string, headers={'Content-Type': 'application/json'})
			response.raise_for_status()
		except requests.exceptions.HTTPError as httperr:
			logger.warning('Xml Request failed: http error - ' + str(httperr.args))
			raise
		except requests.exceptions.Timeout:
			logger.warning('Xml Request failed: Request Timeout')
			raise
		except requests.exceptions.TooManyRedirects:
			logger.warning('Xml Request failed: Too Many Redirects')
			raise
		except:
			raise

def main():
	setupLogger()
	twitter_api = setupTwitterApi(getSecrets())
	
	while True:
		try:
			config = getConfig()
			logger.debug('Get tweets.')
			# 1069315048743432192
			tweets = []
			for name, last_id in config['users'].items():
				for tweet in reversed(getTweets(twitter_api, name, last_id)):
					if tweet.id > last_id:
						last_id = config['users'][name] = tweet.id
					tweets.append(tweet)
					logger.debug('Tweet -> ' + str(tweet))

			logger.debug('Found (' + str(len(tweets)) + ') new tweets.')

			if tweets:
				postToHook(getSecrets(), buildJsonStringFromTweets(tweets))
				saveConfig(config)

		except requests.exceptions.RequestException as rerr:
			logger.warning(str(rerr))
		except:
			logger.warning(sys.exc_info()[0])
			raise

		logger.debug('Sleeping for ' + str(config['period']) + ' minutes')
		time.sleep(config['period'] * 60)

if __name__ == "__main__":
	main()