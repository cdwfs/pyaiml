# This class implements the AIML pattern-matching algorithm described
# by Dr. Richard Wallace at the following site:
# http://www.alicebot.org/documentation/matching.html

import marshal
import re
import string

class PatternMgr:
	# special dictionary keys
	__UNDERSCORE = 0
	__STAR       = 1
	__TEMPLATE   = 2
	__THAT       = 3
	
	def __init__(self):
		self.__root = {}
		self.__templateCount = 0

	def dump(self):
		pprint.pprint(self.__root)

	def save(self, filename):
		"Dumps the current patterns to a file.  To restore later, use restore()."
		try:
			outFile = open(filename, "wb")
			marshal.dump(self.__templateCount, outFile)
			marshal.dump(self.__root, outFile)
			outFile.close()
		except Exception, e:
			print "Error saving PatternMgr to file %s:" % filename
			raise Exception, e

	def restore(self, filename):
		"Restores a previously save()d collection of patterns."
		try:
			inFile = open(filename, "rb")
			self.__templateCount = marshal.load(inFile)
			self.__root = marshal.load(inFile)
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
		node = self.__root
		for word in string.split(pattern):
			key = word
			if key == "_":
				key = self.__UNDERSCORE
			elif key == "*":
				key = self.__STAR
			if not node.has_key(key):
				node[key] = {}
			node = node[key]

		# navigate further down, if a non-empty "that" pattern was included
		if len(that) > 0:
			if not node.has_key(self.__THAT):
				node[self.__THAT] = {}
			for word in string.split(that):
				key = word
				if key == "_":
					key = self.__UNDERSCORE
				elif key == "*":
					key = self.__STAR
				if not node.has_key(key):
					node[key] = {}
				node = node[key]

		# add the template.
		if not node.has_key(self.__TEMPLATE):
			self.__templateCount += 1	
		node[self.__TEMPLATE] = template

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
		return self.__match(string.split(input), self.__root)

	def __match(self, words, root):
		"Behind-the-scenes recursive pattern-matching function."

		# base-case: if the word list is empty, return the current node's
		# template.
		if len(words) == 0:
			try:
				return root[self.__TEMPLATE]
			except KeyError:
				return None
		
		first = words[0]
		suffix = words[1:]
		
		# Check underscore
#		if root.has_key(self.__UNDERSCORE):
#			# Must include the case where suf is [] in order to handle the case
#			# where a * or _ is at the end of the pattern.
#			for j in range(len(suffix)+1):
#				suf = suffix[j:]
#				template = self.__match(suf, root[self.__UNDERSCORE])
#				if template is not None:
#					return template

		# Check first
		if root.has_key(first):
			template = self.__match(suffix, root[first])
			if template is not None:
				return template
			
		# check star
		if root.has_key(self.__STAR):
			# Must include the case where suf is [] in order to handle the case
			# where a * or _ is at the end of the pattern.
			for j in range(len(suffix)+1):
				suf = suffix[j:]
				template = self.__match(suf, root[self.__STAR])
				if template is not None:
					return template

		# No matches were found.
		return None

	def numTemplates(self):
		"Returns the number of templates currently stored."
		return self.__templateCount
			