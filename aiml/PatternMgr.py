# This class implements the AIML pattern-matching algorithm described
# by Dr. Richard Wallace at the following site:
# http://www.alicebot.org/documentation/matching.html

import marshal
import re
import string

class PatternMgr:
	# special dictionary keys
	_UNDERSCORE = 0
	_STAR       = 1
	_TEMPLATE   = 2
	_THAT       = 3
	
	def __init__(self):
		self._root = {}
		self._templateCount = 0

	def dump(self):
		pprint.pprint(self._root)

	def save(self, filename):
		"Dumps the current patterns to a file.  To restore later, use restore()."
		try:
			outFile = open(filename, "wb")
			marshal.dump(self._templateCount, outFile)
			marshal.dump(self._root, outFile)
			outFile.close()
		except Exception, e:
			print "Error saving PatternMgr to file %s:" % filename
			raise Exception, e

	def restore(self, filename):
		"Restores a previously save()d collection of patterns."
		try:
			inFile = open(filename, "rb")
			self._templateCount = marshal.load(inFile)
			self._root = marshal.load(inFile)
			inFile.close()
		except Exception, e:
			print "Error restoring PatternMgr from file %s:" % filename
			raise Exception, e

	def add(self, pattern, that, template):
		"Adds a pattern/that/template tuple to the node tree."
		# TODO: make sure words contains only legal characters
		# (alphanumerics,*,_)

		# Navigate through the node tree to the template's location, adding
		# nodes if necessary.
		node = self._root
		for word in string.split(pattern):
			key = word
			if key == "_":
				key = self._UNDERSCORE
			elif key == "*":
				key = self._STAR
			if not node.has_key(key):
				node[key] = {}
			node = node[key]

		# navigate further down, if a non-empty "that" pattern was included
		if len(that) > 0:
			if not node.has_key(self._THAT):
				node[self._THAT] = {}
			for word in string.split(that):
				key = word
				if key == "_":
					key = self._UNDERSCORE
				elif key == "*":
					key = self._STAR
				if not node.has_key(key):
					node[key] = {}
				node = node[key]

		# add the template.
		if not node.has_key(self._TEMPLATE):
			self._templateCount += 1	
		node[self._TEMPLATE] = template

	def match(self, pattern):
		"""
		Returns the template which is the closest match to pattern.

		Returns None if no template is found.
		"""
		# Mutilate the input.  Remove all punctuation and convert the
		# text to all caps.
		input = string.upper(pattern)
		input = re.sub("[^A-Z0-9_* ]", "", input)
		
		# Pass the input off to the recursive call
		return self._match(string.split(input), self._root)

	def _match(self, words, root):
		"Behind-the-scenes recursive pattern-matching function."

		# base-case: if the word list is empty, return the current node's
		# template.
		if len(words) == 0:
			try:
				return root[self._TEMPLATE]
			except KeyError:
				return None
		
		first = words[0]
		suffix = words[1:]
		
		# Check underscore
#		if root.has_key(self._UNDERSCORE):
#			# Must include the case where suf is [] in order to handle the case
#			# where a * or _ is at the end of the pattern.
#			for j in range(len(suffix)+1):
#				suf = suffix[j:]
#				template = self._match(suf, root[self._UNDERSCORE])
#				if template is not None:
#					return template

		# Check first
		if root.has_key(first):
			template = self._match(suffix, root[first])
			if template is not None:
				return template
			
		# check star
		if root.has_key(self._STAR):
			# Must include the case where suf is [] in order to handle the case
			# where a * or _ is at the end of the pattern.
			for j in range(len(suffix)+1):
				suf = suffix[j:]
				template = self._match(suf, root[self._STAR])
				if template is not None:
					return template

		# No matches were found.
		return None

	def numTemplates(self):
		"Returns the number of templates currently stored."
		return self._templateCount
			