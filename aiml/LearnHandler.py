from xml.sax.handler import ContentHandler

class LearnHandler(ContentHandler):
	def __init__(self):
		self.categories = {}
		self.__inPattern  = False
		self.__inThat     = False
		self.__inTemplate = False
		self.__currentPattern = ""
		self.__currentThat    = ""
		self.__atomStack = []

	def startElement(self, name, attr):
		if name == "pattern":
			# starting a new pattern.  We currently ignore the possibility of
			# any XML tags in the pattern.
			self.__inPattern = True
			self.__currentPattern = ""
		elif name == "that" and not self.__inTemplate:
			# <that/> has a different meaning when it appears inside a
			# template. Right now we're only interested in the <category>-level
			# <that> pattern.
			self.__inThat = True
			self.__currentThat = ""
		elif name == "template":
			# starting a new template
			self.__inTemplate = True
			self.__atomStack = []
			self.__atomStack.append(['template',{}])
		elif self.__inPattern:
			# We currently ignore all XML elements inside patterns.
			self.__currentPattern += " <%s" % name.encode("Latin-1")
			for k,v in attr.items():
				self.__currentPattern += '%s="%s"' % (k,v)
			self.__currentPattern += ">"
		elif self.__inThat:
			# We currently ignore all XML elements inside <that> patterns.
			pass
		elif self.__inTemplate:
			# Starting a new element inside the current pattern
			self.__atomStack.append([name.encode("Latin-1"),attr])			
		else:
			pass # ignore all other elements

	def characters(self, ch):
		if self.__inPattern:
			# Adding text to the current pattern.
			self.__currentPattern += ch.encode("Latin-1")
		elif self.__inThat:
			self.__currentThat += ch.encode("Latin-1")
		elif self.__inTemplate:
			# Add a new text element to the atom at the top of the atom stack.
			self.__atomStack[-1].append(ch.encode("Latin-1"))
		else:
			pass # ignore all other characters

	def endElement(self, name):
		if self.__inPattern:
			if name == "pattern":
				# End the current pattern.
				self.__inPattern = False
			else:
				# We currently ignore all XML elements inside patterns.
				pass
		elif self.__inThat:
			if name == "that":
				# End the current that pattern.
				self.__inThat = False
			else:
				# We currently ignore all XML elements inside <that> patterns.
				pass
		elif self.__inTemplate:
			if name == "template":
				# End the current template.  Store the current pattern/that and
				# atom in the categories dictionary.
				key = (self.__currentPattern.strip(), self.__currentThat.strip())
				self.categories[key] = self.__atomStack[-1]
				self.__inTemplate = False
			else:
				# End of an element inside the current template.  Append the
				# atom at the top of the stack onto the one beneath it.
				atom = self.__atomStack.pop()
				self.__atomStack[-1].append(atom)
		else:
			pass # ignore all other elements