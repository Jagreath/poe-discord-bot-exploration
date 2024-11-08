from html.parser import HTMLParser

class Node():
	def __init__(self, tag='', attributes=[]):
		self.tag = tag
		self.attributes = {v[0]:v[1] for v in attributes}
		self.data = ''
		self.children = []
		self.classNames = []
		self.id = ''

		if 'class' in self.attributes:
			self.classNames = self.attributes['class'].split()
		if 'id' in self.attributes:
			self.id = self.attributes['id']

	def __str__(self):
		o_str = '<' + self.tag
		for k,v in self.attributes.items():
			o_str = o_str + ' ' + str(k) + '="' + str(v) + '"'
		if len(self.children):
			o_str = o_str + '>[' + str(len(self.children)) + ' children]' + self.data + '</' + self.tag + '>'
		elif self.data:
			o_str = o_str + '>' + self.data + '</' + self.tag + '>'
		else:
			o_str = o_str + ' />'
		return o_str

	def append(self, child):
		self.children.append(child)

class NodeParser(HTMLParser):
	def __init__(self):
		self.root = Node(tag='root')
		self.orphans = [self.root]
		super(NodeParser, self).__init__()

	def handle_starttag(self, tag, attrs):
		self.orphans.append(Node(tag=tag,attributes=attrs))

	def handle_endtag(self, tag):
		children = []
		node = self.orphans.pop()
		while node.tag != tag and len(self.orphans) > 0:
			children.append(node)
			node = self.orphans.pop()

		for child in children:
			node.append(child)

		self.orphans[-1].append(node)

	def handle_data(self, data):
		if data and self.orphans[-1]:
			self.orphans[-1].data = data.strip()