from xml.sax.handler import ContentHandler

class LearnHandler(ContentHandler):
	def __init__(self):
		self.categories = {}
		self._inPattern  = False
		self._inThat     = False
		self._inTemplate = False
		self._currentPattern = ""
		self._currentThat    = ""
		self._atomStack = []

	def startElement(self, name, attr):
		if name == "pattern":
			# starting a new pattern.  We currently ignore the possibility of
			# any XML tags in the pattern.
			self._inPattern = True
			self._currentPattern = ""
		elif name == "that" and not self._inTemplate:
			# <that/> has a different meaning when it appears inside a
			# template. Right now we're only interested in the <category>-level
			# <that> pattern.
			self._inThat = True
			self._currentThat = ""
		elif name == "template":
			# starting a new template
			self._inTemplate = True
			self._atomStack = []
			self._atomStack.append(['template',{}])
		elif self._inPattern:
			pass # We currently ignore all XML inside patterns.
		elif self._inThat:
			# We currently ignore all XML elements inside <that> patterns.
			pass
		elif self._inTemplate:
			# Starting a new element inside the current pattern.
			# push the current element onto the atom stack.  First
			# we need to convert 'attr' into a native Python dictionary,
			# so it can later be marshaled.
			attrDict = {}
			for k,v in attr.items():
				attrDict[k] = v
			self._atomStack.append([name.encode("Latin-1"),attrDict])
		else:
			pass # ignore all other elements

	def characters(self, ch):
		if self._inPattern:
			# Adding text to the current pattern.
			self._currentPattern += ch.encode("Latin-1")
		elif self._inThat:
			self._currentThat += ch.encode("Latin-1")
		elif self._inTemplate:
			# Add a new text atom to the atom at the top of the atom stack.
			self._atomStack[-1].append(["text", {}, ch.encode("Latin-1")])
		else:
			pass # ignore all other characters

	def endElement(self, name):
		if self._inPattern:
			if name == "pattern":
				# End the current pattern.
				self._inPattern = False
			else:
				# We currently ignore all XML elements inside patterns.
				pass
		elif self._inThat:
			if name == "that":
				# End the current that pattern.
				self._inThat = False
			else:
				# We currently ignore all XML elements inside <that> patterns.
				pass
		elif self._inTemplate:
			if name == "template":
				# End the current template.  Store the current pattern/that and
				# atom in the categories dictionary.
				key = (self._currentPattern.strip(), self._currentThat.strip())
				self.categories[key] = self._atomStack[-1]
				self._inTemplate = False
			else:
				# End of an element inside the current template.  Append the
				# atom at the top of the stack onto the one beneath it.
				atom = self._atomStack.pop()
				self._atomStack[-1].append(atom)
		else:
			pass # ignore all other elements