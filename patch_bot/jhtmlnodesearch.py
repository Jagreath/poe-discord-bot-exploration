import re
#from jhtmlnodeparser import Node

class NodeSearcher():
	SELECTOR_PATTERN = re.compile(r'\s*(((\S*)\#(\S+))|((\S+)\[(\S+)\=(\S+)\])|((\S*)\.(\S+))|(\S+))+\s*')

	def __init__(self, selector):
		self.__criteria = []
		for match_groups in NodeSearcher.SELECTOR_PATTERN.findall(selector):
			self.__criteria.append(NodeCriteria(match_groups))

	def is_valid(self):
		for c in self.__criteria:
			if not c.is_valid():
				return False
		return True

	def __context_search(self, refNode, criteria):
		results = []
		if criteria.match(refNode):
			results.append(refNode)
		for child in refNode.children:
			results = results + self.__context_search(child, criteria)
		return results

	def results(self, rootNode):
		criteria = self.__criteria[:]
		c = criteria.pop(0)
		results = [rootNode]
		while c:
			next_results = []
			for r in results:
				next_results = next_results + self.__context_search(r, c)
			if len(criteria) > 0:
				c = criteria.pop(0)
			else:
				c = None
			results = next_results

		return results

class NodeCriteria():
	def __init__(self, match_groups):
		self.id = ''
		self.tag = ''
		self.className = ''
		self.attribute = ''
		self.attributeValue = ''

		if match_groups[1]:
			# id
			self.tag = match_groups[2]
			self.id = match_groups[3]
		elif match_groups[4]:
			# attribute
			self.tag = match_groups[5]
			self.attribute = match_groups[6]
			self.attributeValue = match_groups[7]
		elif match_groups[8]:
			# class
			self.tag = match_groups[9]
			self.className = match_groups[10]
		elif match_groups[11]:
			# just tag
			self.tag = match_groups[11]

	def is_valid(self):
		return self.id or self.tag or self.className or (self.attribute and self.attributeValue)

	def match(self, node):
		if not self.is_valid():
			return False
		return (not self.id or self.id == node.id) and (not self.tag or self.tag == node.tag) and (not self.className or self.className in node.classNames) and (not self.attribute or (self.attribute in node.attributes and node.attributes[self.attribute] == self.attributeValue))