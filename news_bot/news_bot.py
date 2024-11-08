"""
Simple bot to poll pathofexile.com rss news feed and post the updates to a single webhook uri.
"""

import time
from datetime import datetime
import json
import requests
import xmltodict
import html2markdown
import logging

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

def getXml(config):
	"""Get xml from remote source"""
	logger.debug('Getting xml')

	if config['news_uri'].startswith('http'):
		try:
			response = requests.get(config['news_uri'], timeout=30)
			response.raise_for_status()
			return response.text
		except requests.exceptions.HTTPError as err:
			logger.warning('Xml Request failed: http error - ' + str(err.args))
			raise
		except requests.exceptions.Timeout:
			logger.warning('Xml Request failed: Request Timeout')
			raise
		except requests.exceptions.TooManyRedirects:
			logger.warning('Xml Request failed: Too Many Redirects')
			raise
		except:
			raise

	try:
		with open(config['news_uri']) as file:
			return file.read()
	except:
		raise

def convertXmlToDictionary(xml):
	"""Create data dictionary from xml"""
	logger.debug('Building dictionary')

	try:
		return xmltodict.parse(xml)
	except xmltodict.ParsingInterrupted:
		logger.warning('Xml parsing failed: TODO')
		raise
	except ValueError as err:
		logger.warning('Xml parsing failed:' + str(err.args))
		raise
	except:
		raise

def selectDataTitle(data):
	"""Select feed title from feed data"""
	try:
		return data['rss']['channel']['title']
	except:
		logger.warning('Unable to find data title')
		raise

def selectDataUrl(data):
	"""select feed url from feed data"""
	try:
		return data['rss']['channel']['link']
	except:
		logger.warning('Unable to find data uri')
		raise

def selectDataIcon(data):
	"""Select feed icon url from feed data"""
	try:
		return data['rss']['channel']['image']['url']
	except:
		logger.warning('Unable to find image uri')
		raise

def selectItems(data):
	"""Select items from feed data"""
	try:
		return data['rss']['channel']['item']
	except:
		logger.warning('Unable to find items')
		raise

def selectItemPublicationDate(item):
	"""Parse publication date as datetime object from feed item"""
	try:
		return datetime.strptime(item['pubDate'], '%a, %d %b %Y %H:%M:%S %z')
	except:
		raise

def selectItemTitle(item):
	"""Get item title from feed item"""
	try:
		return item['title']
	except:
		raise

def getItemDescription(item):
	"""Get item description from feed item"""
	try:
		return html2markdown.convert(item['description'])
	except:
		logger.warning('Unable to get item description')
		raise

def getItemUrl(item):
	"""Get item url from feed item"""
	try:
		return item['link']
	except:
		logger.warning('Unable to get item url')
		raise

def buildJsonStringFromItems(xml_dict, items):
	"""Build json string from feed items"""

	embeds = []
	for item in items:
		embeds.append({
			'author': {
				'name': selectDataTitle(xml_dict),
				'url': selectDataUrl(xml_dict),
				'icon_url': selectDataIcon(xml_dict)
			},
			'title': selectItemTitle(item),
			'color': 14393088,
			'description': getItemDescription(item),
			'url': getItemUrl(item),
			'footer': {
				"text" : selectItemPublicationDate(item).strftime('%a, %d %b %Y %H:%M %Z')
			}
		})

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
			logger.warning('Xml Request failed: http error - ' + str(httperr))
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

	while True:
		try:
			config = getConfig()
			last_post = datetime.fromisoformat(config['last_post'])

			logger.debug('Checking for new posts. Last post was: ' + last_post.isoformat())

			xml = getXml(config)
			xml_dict = convertXmlToDictionary(xml)
			items = list(reversed(selectItems(xml_dict)))

			logger.debug('Filtering to new posts.')
			
			for item in items[:]:
				if selectItemPublicationDate(item) > last_post:
					last_post = selectItemPublicationDate(item)
				else:
					items.remove(item)

			logger.debug('(' + str(len(items)) + ') new posts found.')

			if len(items):
				postToHook(getSecrets(), buildJsonStringFromItems(xml_dict, items))

				config['last_post'] = last_post.isoformat()
				saveConfig(config)
		except requests.exceptions.RequestException as rerr:
			logger.warning(str(rerr))
		except:
			logger.exception()
			raise

		logger.debug('Sleeping for ' + str(config['period']) + ' minutes')
		time.sleep(config['period'] * 60)

if __name__ == "__main__":
	main()