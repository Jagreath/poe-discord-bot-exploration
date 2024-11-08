"""
Simple bot to poll pathofexile.com rss news and patch note feeds every X minutes.
"""

import time
from datetime import datetime
from datetime import timezone
import json
import requests
from jhtmlnodeparser import NodeParser
from jhtmlnodesearch import NodeSearcher
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

def getHtml(config):
	"""Get html from remote source"""
	if config['notes_uri'].startswith('http'):
		try:
			response = requests.get(config['notes_uri'], timeout=30)
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
		with open(config['notes_uri']) as file:
			return file.read()
	except:
		raise

def getTitleAndUriFromThreadNode(node):
	try:
		title_searcher = NodeSearcher('div.thread_title div.title a')
		title = ''
		title_uri = ''
		title_results = title_searcher.results(node)
		if len(title_results):
			title = title_results[0].data
			title_uri = 'https://www.pathofexile.com' + title_results[0].attributes['href']
		return title, title_uri
	except:
		raise

def getPubDateFromThreadNode(node):
	try:
		date_searcher = NodeSearcher('span.post_date')
		pub_date = datetime.utcnow().replace(year = datetime.utcnow().year + 1)
		date_results = date_searcher.results(node)
		if len(date_results):
			pub_date = datetime.strptime(date_results[0].data.lstrip(', ').rstrip(), '%b %d, %Y, %I:%M:%S %p').astimezone(tz=timezone.utc)
		return pub_date
	except:
		raise

def getAuthorAndUriFromThreadNode(node):
	try:
		author_searcher = NodeSearcher('div.postBy span.post_by_account a')
		author = ''
		author_uri = ''
		author_results = author_searcher.results(node)
		if len(author_results):
			author = author_results[0].data
			author_uri = 'https://www.pathofexile.com/' + author_results[0].attributes['href']
		return author, author_uri
	except:
		raise

def buildJsonStringFromNodes(config, nodes):
	"""Build json string from thread nodes"""

	embeds = []
	for node in nodes:
		author, author_uri = getAuthorAndUriFromThreadNode(node)
		title, title_uri = getTitleAndUriFromThreadNode(node)
		embeds.append({
			'author': {
				'name': author,
				'url': author_uri,
				'icon_url': config['icon_uri']
			},
			'title': title,
			'color': 15822337,
			'url': title_uri,
			'footer': {
				"text" : getPubDateFromThreadNode(node).strftime('%a, %d %b %Y %H:%M %Z')
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
	
	while True:
		try:
			config = getConfig()
			last_post = datetime.fromisoformat(config['last_post'])
			logger.debug('Checking for new posts. Last post was: ' + last_post.isoformat())

			html = getHtml(config)

			parser = NodeParser()
			logger.debug('Parsing html string.')
			parser.feed(html)

			logger.debug('Create list of nodes for each thread.')
			thread_searcher = NodeSearcher('table.forumTable td.thread')
			thread_nodes = thread_searcher.results(parser.root)

			logger.debug('Filtering to new posts.')
			nodes = []
			for node in reversed(thread_nodes):
				pub_date = getPubDateFromThreadNode(node)
				if pub_date > last_post:
					last_post = pub_date
					nodes.append(node)
			
			logger.debug('(' + str(len(nodes)) + ') new posts found.')

			if nodes:
				postToHook(getSecrets(), buildJsonStringFromNodes(config, nodes))

				config['last_post'] = last_post.isoformat()
				saveConfig(config)
		except requests.exceptions.RequestException as rerr:
			logger.warning(str(rerr))
		except:
			logger.exception()
			raise

		logger.debug('Sleeping for ' + str(config['period']) + ' minutes.')
		time.sleep(config['period'] * 60)

if __name__ == "__main__":
	main()