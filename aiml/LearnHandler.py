from xml.sax.handler import ContentHandler
from xml.sax.xmlreader import Locator

class AimlParserError(Exception): pass

class LearnHandler(ContentHandler):
	# The legal states of the AIML parser
	_STATE_OutsideAiml    = 0
	_STATE_InsideAiml     = 1
	_STATE_InsideCategory = 2
	_STATE_InsidePattern  = 3
	_STATE_AfterPattern   = 4
	_STATE_InsideThat     = 5
	_STATE_AfterThat      = 6
	_STATE_InsideTemplate = 7
	_STATE_AfterTemplate  = 8
	
	def __init__(self, encoding = "Latin-1"):
		self.categories = {}
		self._encoding = encoding
		self._state = self._STATE_OutsideAiml
		self._version = ""
		self._namespace = ""
		self._forwardCompatibleMode = False
		self._currentPattern = ""
		self._currentThat    = ""
		self._currentTopic   = ""
		self._insideTopic = False
		self._currentUnknown = "" # the name of the current unknown element
		self._atomStack = []
		self._locator = Locator()
		self.setDocumentLocator(self._locator)

	def _location(self):
		"Returns a string describing the current location in the source file."
		line = self._locator.getLineNumber()
		column = self._locator.getColumnNumber()
		return "(line %d, column %d)" % (line, column)

	def startElement(self, name, attr):
		# If we're inside an unknown element, ignore everything until we're out again
		if self._currentUnknown != "":
			return
		
		if name == "aiml":
			# <aiml> tags are only legal in the OutsideAiml state
			if self._state != self._STATE_OutsideAiml:
				raise AimlParserError, "Unexpected <aiml> tag "+self._location()
			self._state = self._STATE_InsideAiml
			self._insideTopic = False
			self._currentTopic = ""
			try: self._version = attr["version"]
			except KeyError: raise AimlParserError, "Missing 'version' attribute in <aiml> tag "+self._location()
			try:
				self._namespace = attr["xmlns"]
				if self._version == "1.0.1" and self._namespace != "http://alicebot.org/2001/AIML-1.0.1":
					raise AimlParserError, "Incorrect namespace for AIML v1.0.1 "+self._location()
			except KeyError:
				if self._version != "1.0":
					raise AimlParserError, "Missing 'version' and/or 'xmlns' attribute(s) in <aiml> tag "+self._location()
		elif self._state == self._STATE_OutsideAiml:
			# If we're outside of an AIML element, we ignore all tags.
			return
		elif name == "topic":
			# <topic> tags are only legal in the InsideAiml state, and only
			# if we're not already inside a topic.
			if (self._state != self._STATE_InsideAiml) or self._insideTopic:
				raise AimlParserError, "Unexpected <topic> tag", self._location()
			try: self._currentTopic = attr['name']
			except AttributeError:
				raise AimlParserError, "Missing 'name' attribute in <topic> tag "+self._location()
			self._insideTopic = True
		elif name == "category":
			# <category> tags are only legal in the InsideAiml state
			if self._state != self._STATE_InsideAiml:
				raise AimlParserError, "Unexpected <category> tag "+self._location()
			self._state = self._STATE_InsideCategory
			self._currentPattern = ""
			self._currentThat = ""
			# If we're not inside a topic, the topic is implicitly set to *
			if not self._insideTopic: self._currentTopic = "*"
			self._atomStack = []
		elif name == "pattern":
			# <pattern> tags are only legal in the InsideCategory state
			if self._state != self._STATE_InsideCategory:
				raise AimlParserError, "Unexpected <pattern> tag "+self._location()
			self._state = self._STATE_InsidePattern
		elif name == "that" and self._state == self._STATE_AfterPattern:
			# <that> are legal either inside a <template> element, or
			# inside a <category> element, between the <pattern> and the
			# <template> elements.  This clause handles the latter case.
			self._state = self._STATE_InsideThat
		elif name == "template":
			# <template> tags are only legal in the AfterPattern and AfterThat
			# states
			if self._state not in [self._STATE_AfterPattern, self._STATE_AfterThat]:
				raise AimlParserError, "Unexpected <template> tag "+self._location()
			# if no <that> element was specified, it is implicitly set to *
			if self._state == self._STATE_AfterPattern:
				self._currentThat = "*"
			self._state = self._STATE_InsideTemplate
			self._atomStack.append(['template',{}])
		elif self._state == self._STATE_InsidePattern:
			# Certain tags are allowed inside <pattern> elements.
			if name == "bot" and attr.has_key("name") and attr["name"] == "name":
				# Insert a special character string that the PatternMgr will
				# replace with the bot's name.
				self._currentPattern += " BOT_NAME "
			else:
				raise AimlParserError, ("Unexpected <%s> tag " % name)+self._location()
		elif self._state == self._STATE_InsideThat:
			# Certain tags are allowed inside <that> elements.
			if name == "bot" and attr.has_key("name") and attr["name"] == "name":
				# Insert a special character string that the PatternMgr will
				# replace with the bot's name.
				self._currentThat += " BOT_NAME "
			else:
				raise AimlParserError, ("Unexpected <%s> tag " % name)+self._location()
		elif self._state == self._STATE_InsideTemplate:
			# Starting a new element inside the current pattern.
			# Push the current element onto the atom stack.  First
			# we need to convert 'attr' into a native Python dictionary,
			# so it can later be marshaled.
			attrDict = {}
			for k,v in attr.items():
				attrDict[k.encode(self._encoding)] = v.encode(self._encoding)
			self._atomStack.append([name.encode(self._encoding),attrDict])
		else:
			# we're now inside an unknown element.  Ignore everything until it ends.
			if self._version == "1.0.1":
				print ("Warning: unknown <%s> element " % name)+self._location()
			self._currentUnknown = name

	def characters(self, ch):
		if self._state == self._STATE_OutsideAiml:
			# If we're outside of an AIML element, we ignore all text
			return
		elif self._currentUnknown != "":
			# If we're inside an unknown element, ignore all text
			return
		text = ch.encode(self._encoding)
		if self._state == self._STATE_InsidePattern:
			self._currentPattern += text
		elif self._state == self._STATE_InsideThat:
			self._currentThat += text
		elif self._state == self._STATE_InsideTemplate:
			# Add a new text atom to the atom at the top of the atom stack. If
			# there's already a text atom there, simply append the new
			# characters to its contents.
			try: textAtomOnStack = (self._atomStack[-1][-1][0] == "text")
			except IndexError: textAtomOnStack = False
			except KeyError: textAtomOnStack = False
			if textAtomOnStack:
				self._atomStack[-1][-1][2] += text
			else:
				self._atomStack[-1].append(["text", {}, text])
		else:
			# all other text is ignored
			pass
		
	def endElement(self, name):
		if self._state == self._STATE_OutsideAiml:
			# If we're outside of an AIML element, ignore all tags
			return
		if self._currentUnknown != "" and name == self._currentUnknown:
			# see if we're at the end of an unknown element.  If so, we can
			# stop ignoring everything.
			self._currentUnknown = ""
		elif name == "aiml":
			# </aiml> tags are only legal in the InsideAiml state
			if self._state != self._STATE_InsideAiml:
				raise AimlParserError, "Unexpected </aiml> tag "+self._location()
			self._state = self._STATE_OutsideAiml
		elif name == "topic":
			# </topic> tags are only legal in the InsideAiml state, and
			# only if _insideTopic is true.
			if self._state != self._STATE_InsideAiml or not self._insideTopic:
				raise AimlParserError, "Unexpected </topic> tag "+self._location()
			self._insideTopic = False
			self._currentTopic = ""
		elif name == "category":
			# </category> tags are only legal in the AfterTemplate state
			if self._state != self._STATE_AfterTemplate:
				raise AimlParserError, "Unexpected </category> tag "+self._location()
			self._state = self._STATE_InsideAiml
			# End the current category.  Store the current pattern/that and
			# atom in the categories dictionary.
			key = (self._currentPattern.strip(), self._currentThat.strip())
			self.categories[key] = self._atomStack[-1]
		elif name == "pattern":
			# </pattern> tags are only legal in the InsidePattern state
			if self._state != self._STATE_InsidePattern:
				raise AimlParserError, "Unexpected </pattern> tag "+self._location()
			self._state = self._STATE_AfterPattern
		elif name == "that" and self._state == self._STATE_InsideThat:
			# </that> tags are only allowed inside <template> elements or in
			# the InsideThat state.  This clause handles the latter case.
			self._state = self._STATE_AfterThat
		elif name == "template":
			# </template> tags are only allowed in the InsideTemplate state.
			if self._state != self._STATE_InsideTemplate:
				raise AimlParserError, "Unexpected </template> tag "+self._location()
			self._state = self._STATE_AfterTemplate
		elif self._state == self._STATE_InsidePattern:
			# Certain tags are allowed inside <pattern> elements.
			if name not in ["bot"]:
				raise AimlParserError, ("Unexpected </%s> tag " % name)+self._location()
		elif self._state == self._STATE_InsideThat:
			# Certain tags are allowed inside <that> elements.
			if name not in ["bot"]:
				raise AimlParserError, ("Unexpected </%s> tag " % name)+self._location()
		elif self._state == self._STATE_InsideTemplate:
			# End of an element inside the current template.  Append the
			# atom at the top of the stack onto the one beneath it.
			atom = self._atomStack.pop()
			self._atomStack[-1].append(atom)
		else:
			# Unexpected closing tag
			raise AimlParserError, ("Unexpected </%s> tag " % name)+self._location()