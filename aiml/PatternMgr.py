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
			node = node[self._THAT]
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

	def match(self, pattern, that):
		"""
		Returns the template which is the closest match to pattern.
		The optional 'that' parameter contain's the bot's previous response.

		Returns None if no template is found.
		"""
		# Mutilate the input.  Remove all punctuation and convert the
		# text to all caps.
		convertRE = re.compile("[^A-Z0-9_* ]")
		input = string.upper(pattern)
		input = re.sub(convertRE, "", input)
		thatInput = string.upper(that)
		thatInput = re.sub(convertRE, "", thatInput)
		
		# Pass the input off to the recursive call
		patMatch, template = self._match(input.split(), thatInput.split(), self._root)
		return template

	def star(self, pattern, that):
		"Returns a string, the portion of pattern that was matched by a *."
		# Mutilate the input.  Remove all punctuation and convert the
		# text to all caps.
		convertRE = re.compile("[^A-Z0-9_* ]")
		input = string.upper(pattern)
		input = re.sub(convertRE, "", input)
		thatInput = string.upper(that)
		thatInput = re.sub(convertRE, "", thatInput)

		# Pass the input off to the recursive pattern-matcher
		patMatch, template = self._match(input.split(), thatInput.split(), self._root)
		if template == None:
			return ""

		# compare the input string to the matched pattern, word by word.
		words = input.split()
		try: words = words[:words.index(self._THAT)]
		except ValueError:
			pass
		inStar = False
		start = end = j = 0
		for i in range(len(words)):
			# check for the end of the input string
			if patMatch[j] in [self._THAT]:
				break
			if not inStar:
				# if the two words are the same, advance the indices
				if patMatch[j] in [self._STAR, self._UNDERSCORE]:
					# a star is born!
					inStar = True
					start = i
					# if the star is the last element in the pattern, we're done.
					if patMatch[-1] in [self._STAR, self._UNDERSCORE]:
						end = len(words)
						break;
				j += 1 # next word
			else:
				if words[i:] == patMatch[j:]:
					end = i-1
					break
		# extract the star words from the original, unmutilated input.
		if inStar: return string.join(pattern.split()[start:end+1])
		else: return ""

	def _match(self, words, thatWords, root):
		"""Behind-the-scenes recursive pattern-matching function.

Returns a tuple (pat, tem) where pat is a list of nodes, starting at the root
and leading to the matching pattern, and tem is the matched template.
"""
		# base-case: if the word list is empty, return the current node's
		# template.
		if len(words) == 0:
			# if thatWords is empty as well, we're done -- return the template
			# from this node.  Otherwise, recursively pattern-match again using
			# thatWords as the input pattern and the current node's _THAT child
			# as the root.
			pattern = []
			template = None
			if len(thatWords) > 0:
				try:
					pattern, template = self._match(thatWords, [], root[self._THAT])
					if pattern != None:
						pattern = [self._THAT] + pattern
				except KeyError:
					pattern = []
					template = None
			# If we still haven't found anything, return the template from the
			# current node.
			if template == None:
				pattern = []
				try: template = root[self._TEMPLATE]
				except KeyError: template = None
			return (pattern, template)
				
		
		first = words[0]
		suffix = words[1:]
		
		# Check underscore.
		# Note: this is causing problems in the standard AIML set, and is
		# currently disabled.
#		if root.has_key(self._UNDERSCORE):
#			# Must include the case where suf is [] in order to handle the case
#			# where a * or _ is at the end of the pattern.
#			for j in range(len(suffix)+1):
#				suf = suffix[j:]
#				pattern, template = self._match(suf, thatWords, root[self._UNDERSCORE])
#				if template is not None:
#					newPattern = [self._UNDERSCORE] + pattern
#					return (newPattern, template)

		# Check first
		if root.has_key(first):
			pattern, template = self._match(suffix, thatWords, root[first])
			if template is not None:
				newPattern = [first] + pattern
				return (newPattern, template)
			
		# check star
		if root.has_key(self._STAR):
			# Must include the case where suf is [] in order to handle the case
			# where a * or _ is at the end of the pattern.
			for j in range(len(suffix)+1):
				suf = suffix[j:]
				pattern, template = self._match(suf, thatWords, root[self._STAR])
				if template is not None:
					newPattern = [self._STAR] + pattern
					return (newPattern, template)

		# No matches were found.
		return (None, None)

	def numTemplates(self):
		"Returns the number of templates currently stored."
		return self._templateCount
			