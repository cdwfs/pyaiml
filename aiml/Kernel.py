"""
This file contains the public interface to the aiml module.
"""
import DefaultSubs
import Utils
from AimlParser import AimlParser, AimlParserError
from PatternMgr import PatternMgr
from WordSub import WordSub

from ConfigParser import ConfigParser
import glob
import os
import random
import re
import shelve
import string
import sys
import time
import threading
import xml.sax


class Kernel:
    # module constants
    _globalSessionID = "_global" # key of the global session (duh)
    _maxHistorySize = 10 # maximum length of the _inputs and _responses lists
    # special predicate keys
    _inputHistory = "_inputHistory"     # keys to a queue (list) of recent user input
    _outputHistory = "_outputHistory"   # keys to a queue (list) of recent responses.
    _inputStack = "_inputStack"         # Should always be empty in between calls to respond()

    def __init__(self):
        self._verboseMode = True
        self._version = "PyAIML 0.7"
        self._brain = PatternMgr()
        self._respondLock = threading.RLock()

        # set up the sessions        
        self._sessions = {}
        self._sessionsArePersistent = False
        self._sessionsDir = "sessions"
        self._addSession(self._globalSessionID)

        # Set up the bot predicates
        self._botPredicates = {}
        self.setBotPredicate("name", "Nameless")

        # set up the word substitutors (subbers):
        self._subbers = {}
        self._subbers['gender'] = WordSub(DefaultSubs.defaultGender)
        self._subbers['person'] = WordSub(DefaultSubs.defaultPerson)
        self._subbers['person2'] = WordSub(DefaultSubs.defaultPerson2)
        self._subbers['normal'] = WordSub(DefaultSubs.defaultNormal)
        
        # set up the element processors
        self._elementProcessors = {
            "bot":          self._processBot,
            "condition":    self._processCondition,
            "date":         self._processDate,
            "formal":       self._processFormal,
            "gender":       self._processGender,
            "get":          self._processGet,
            "gossip":       self._processGossip,
            "id":           self._processId,
            "input":        self._processInput,
            "javascript":   self._processJavascript,
            "learn":        self._processLearn,
            "li":           self._processLi,
            "lowercase":    self._processLowercase,
            "person":       self._processPerson,
            "person2":      self._processPerson2,
            "random":       self._processRandom,
            "text":         self._processText,
            "sentence":     self._processSentence,
            "set":          self._processSet,
            "size":         self._processSize,
            "sr":           self._processSr,
            "srai":         self._processSrai,
            "star":         self._processStar,
            "system":       self._processSystem,
            "template":     self._processTemplate,
            "that":         self._processThat,
            "thatstar":     self._processThatstar,
            "think":        self._processThink,
            "topicstar":    self._processTopicstar,
            "uppercase":    self._processUppercase,
            "version":      self._processVersion,
        }

    def __del__(self):
        # close the session files
        for id in self._sessions.keys():
            if self._sessionsArePersistent:
                self._sessions[id].close()
            self._sessions.pop(id)
    def bootstrap(self, brainFile = None, learnFiles = [], commands = []):
        """
        Prepares a Kernel object for use.

        If a brainFile argument is provided, the Kernel attempts to
        load the brain at the specified filename.

        If learnFiles is provided, the Kernel attempts to load the
        specified AIML files.

        Finally, each of the input strings in the commands list is
        passed to respond().
        """
        start = time.clock()
        if brainFile:
            self.loadBrain(brainFile)

        # learnFiles might be a string, in which case it should be
        # turned into a single-element list.
        learns = learnFiles
        try: learns = [ learnFiles + "" ]
        except: pass
        for file in learns:
            self.learn(file)
            
        # ditto for commands
        cmds = commands
        try: cmds = [ commands + "" ]
        except: pass
        for cmd in cmds:
            print self._respond(cmd, self._globalSessionID)
            
        if self._verboseMode:
            print "Kernel bootstrap completed in %.2f seconds" % (time.clock() - start)

    def verbose(self, isVerbose = True):
        "Enabled/disables verbose output mode."
        self._verboseMode = isVerbose

    def version(self):
        "Returns the Kernel's version string."
        return self._version

    def numCategories(self):
        "Returns the number of categories the Kernel has learned."
        # there's a one-to-one mapping between templates and categories
        return self._brain.numTemplates()

    def setBotName(self, newName):
        "Sets the bot's name.  THIS FUNCTION IS DEPRECATED -- use setBotPredicate instead"
        print "NOTE: Kernel.setBotName() is deprecated. Use Kernel.setBotPredicate() instead."
        self.setBotPredicate("name", newName)
    def getBotName(self):
        "Returns the bot's name. THIS FUNCTION IS DEPRECATED -- use getBotPredicate instead."
        print "NOTE: Kernel.getBotName() is deprecated. Use Kernel.getBotPredicate() instead."
        return self.getBotPredicate("name")
        
    def resetBrain(self):
        "Erases all of the bot's knowledge."
        del(self._brain)
        self.__init__()

    def loadBrain(self, filename):
        """
        Attempts to load a previously-saved 'brain' from the
        specified filename.

        NOTE: the current contents of the 'brain' will be discarded!
        """
        if self._verboseMode: print "Loading brain from %s..." % filename,
        start = time.clock()
        self._brain.restore(filename)
        if self._verboseMode:
            end = time.clock() - start
            print "done (%d categories in %.2f seconds)" % (self._brain.numTemplates(), end)

    def saveBrain(self, filename):
        "Dumps the contents of the bot's brain to a file on disk."
        if self._verboseMode: print "Saving brain to %s..." % filename,
        start = time.clock()
        self._brain.save(filename)
        if self._verboseMode:
            print "done (%.2f seconds)" % (time.clock() - start)

    def getPredicate(self, name, sessionID = _globalSessionID):
        "Retrieves the value of the predicate 'name' from the specified session."
        try: return self._sessions[sessionID][name]
        except KeyError: return ""

    def setPredicate(self, name, value, sessionID = _globalSessionID):
        "Sets the value of the predicate 'name' in the specified session."
        self._addSession(sessionID) # add the session, if it doesn't already exist.
        self._sessions[sessionID][name] = value

    def getBotPredicate(self, name):
        "Retrieves the value of the specified bot predicate."
        try: return self._botPredicates[name]
        except KeyError: return ""

    def setBotPredicate(self, name, value):
        "Sets the value of the specified bot predicate."
        self._botPredicates[name] = value
        # Clumsy hack: if updating the bot name, we must update the
        # name in the brain as well
        if name == "name":
            self._brain.setBotName(self.getBotPredicate("name"))

    def loadSubs(self, filename):
        """Load a substitutions file.  The file must be in the Windows-style INI
format (see the standard ConfigParser module docs for information on
this format).  Each section of the file is loaded into its own substituter."""
        inFile = file(filename)
        parser = ConfigParser()
        parser.readfp(inFile, filename)
        inFile.close()
        for s in parser.sections():
            # Add a new WordSub instance for this section.  If one already
            # exists, delete it.
            if self._subbers.has_key(s):
                del(self._subbers[s])
            self._subbers[s] = WordSub()
            # iterate over the key,value pairs and add them to the subber
            for k,v in parser.items(s):
                self._subbers[s][k] = v

    def persistentSessions(self, enable, sessionsDir = None):
        """Enables/disables persistent sessions.

If disabled, all session data is lost when the Kernel is destroyed.
The optional sessionsDir argument specifies a directory where persistent
session data should be stored.  Calling this function erases all existing
session data in memory, so it should be called shortly after startup."""
        if enable == self._sessionsArePersistent:
            return
        self._sessionsArePersistent = enable
        if enable:
            # store the sessions dir
            if sessionsDir is not None: self._sessionsDir = sessionsDir
            # delete existing sessions
            for id in self._sessions.keys():
                self._sessions.pop(id)
        else:
            # close and remove all existing sessions
            for id in self._sessions.keys():
                self._sessions[id].close()
                self._sessions.pop(id)
        

    def _addSession(self, sessionID):
        "Creates a new session with the specified ID string."
        if self._sessions.has_key(sessionID):
            return
        # Create the session.  Use either a dict or a shelve object,
        # depending on whether sessions should be persistent.
        if self._sessionsArePersistent:
            if not os.path.isdir(self._sessionsDir):
                os.mkdir(self._sessionsDir)
            sessionFile = "%s/%s.db" % (self._sessionsDir, sessionID)
            self._sessions[sessionID] = shelve.open(sessionFile, protocol=-1)
        else:
            self._sessions[sessionID] = {}
        # Initialize the special predicates
        if not self._sessions[sessionID].has_key(self._inputHistory):
            self._sessions[sessionID][self._inputHistory] = []
        if not self._sessions[sessionID].has_key(self._outputHistory):
            self._sessions[sessionID][self._outputHistory] = []
        if not self._sessions[sessionID].has_key(self._inputStack):
            self._sessions[sessionID][self._inputStack] = []
        
    def _deleteSession(self, sessionID):
        "Deletes the specified session."
        if self._sessions.has_key(sessionID):
            _sessions.pop(sessionID)

    def learn(self, filename):
        "Loads and learns the contents of the specified AIML file (which may include wildcards)"
        for f in glob.glob(filename):
            if self._verboseMode: print "Loading %s..." % f,
            start = time.clock()
            # Load and parse the AIML file.
            handler = AimlParser()
            try: xml.sax.parse(f, handler)
            except AimlParserError, msg:
                print "\nPARSE ERROR in file %s:\n%s" % (f,msg)
                continue
            except xml.sax.SAXParseException, msg:
                print "\nPARSE ERROR in file %s:\n%s" % (f,msg)
                continue
            # store the pattern/template pairs in the PatternMgr.
            for key,tem in handler.categories.items():
                self._brain.add(key,tem)
            # Parsing was successful.
            if self._verboseMode:
                print "done (%.2f seconds)" % (time.clock() - start)

    def respond(self, input, sessionID = _globalSessionID):
        "Returns the Kernel's response to the input string."
        if len(input) == 0:
            return ""
        
        # prevent other threads from stomping all over us.
        self._respondLock.acquire()

        # Add the session, if it doesn't already exist
        self._addSession(sessionID)

        # split the input into discrete sentences
        sentences = Utils.sentences(input)
        finalResponse = ""
        for s in sentences:
            # Add the input to the history list before fetching the
            # response, so that <input/> tags work properly.
            inputHistory = self.getPredicate(self._inputHistory, sessionID)
            inputHistory.append(s)
            while len(inputHistory) > self._maxHistorySize:
                inputHistory.pop(0)
            self.setPredicate(self._inputHistory, inputHistory, sessionID)
            
            # Fetch the response
            response = self._respond(s, sessionID)

            # add the data from this exchange to the history lists
            outputHistory = self.getPredicate(self._outputHistory, sessionID)
            outputHistory.append(response)
            while len(outputHistory) > self._maxHistorySize:
                outputHistory.pop(0)
            self.setPredicate(self._outputHistory, outputHistory, sessionID)

            # append this response to the final response.
            finalResponse += (response + "  ")
        finalResponse = finalResponse.strip()

        # sync the session file
        try: self._sessions[sessionID].sync()
        except AttributeError:
            pass # built-in dicts don't need to be sync'd.

        assert(len(self.getPredicate(self._inputStack, sessionID)) == 0)
        
        # release the lock and return
        self._respondLock.release()
        return finalResponse

    # This version of _respond() just fetches the response for some input.
    # It does not mess with the input and output histories.  Recursive calls
    # to respond() spawned from tags like <srai> should call this function
    # instead of respond().
    def _respond(self, input, sessionID):
        "Private version of respond(), does the real work."
        if len(input) == 0:
            return ""

        # push the input onto the input stack
        inputStack = self.getPredicate(self._inputStack, sessionID)
        inputStack.append(input)
        self.setPredicate(self._inputStack, inputStack, sessionID)

        # run the input through the 'normal' subber
        subbedInput = self._subbers['normal'].sub(input)

        # fetch the bot's previous response, to pass to the match()
        # function as 'that'.
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        try: that = outputHistory[-1]
        except IndexError: that = ""
        subbedThat = self._subbers['normal'].sub(that)

        # fetch the current topic
        topic = self.getPredicate("topic", sessionID)
        subbedTopic = self._subbers['normal'].sub(topic)

        # Determine the final response.
        response = ""
        elem = self._brain.match(subbedInput, subbedThat, subbedTopic)
        if elem is None:
            if self._verboseMode: print "No match found for input:", input
        else:
            # Process the element into a response string.
            response += self._processElement(elem, sessionID).strip()
            response += " "
        response = response.strip()

        # pop the top entry off the input stack.
        inputStack = self.getPredicate(self._inputStack, sessionID)
        inputStack.pop()
        self.setPredicate(self._inputStack, inputStack, sessionID)
        
        return response

    def _processElement(self,elem, sessionID):
        # The first element of the 'elem' list is a
        # string describing the type of the element (== the name of
        # the XML tag).  The second element is a dictionary
        # containing attributes passed to the XML tag.  Any
        # remaining elements are element-specific, and should be
        # treated as additional elements.
        try:
            handlerFunc = self._elementProcessors[elem[0]]
        except:
            # Oops -- there's no handler function for this element
            # type!
            if self._verboseMode: print "No handler found for <%s> element" % elem[0]
            return ""
        return handlerFunc(elem, sessionID)


    ######################################################
    ### Individual element-processing functions follow ###
    ######################################################

    # bot
    def _processBot(self, elem, sessionID):
        # Bot elements are used to fetch the value of global,
        # read-only "bot predicates".  The values of these predicates
        # cannot be set using AIML; they must be initialized with
        # Kernel.setBotPredicate().
        attrName = elem[1]['name']
        return self.getBotPredicate(attrName)
        
    # condition
    def _processCondition(self, elem, sessionID):
        # Condition elements come in three flavors.  Each has different
        # attributes, and each handles their contents differently.
        attr = None
        response = ""
        attr = elem[1]
        
        # The simplest case is when the condition tag has both a
        # 'name' and a 'value' attribute.  In this case, if the
        # predicate 'name' has the value 'value', then the contents of
        # the element are processed and returned.
        if attr.has_key('name') and attr.has_key('value'):
            val = self.getPredicate(attr['name'], sessionID)
            if val == attr['value']:
                for e in elem[2:]:
                    response += self._processElement(e,sessionID)
                return response
        
        # If the condition element has only a 'name' attribute, then its
        # contents are a series of <li> elements, each of which has a
        # 'value' attribute.  The list is scanned from top to bottom
        # until a match is found.  Optionally, the last <li> element can
        # have no 'value' attribute, in which case it is processed and
        # returned if no other match is found.
        #
        # If the condition element has neither a 'name' nor a 'value'
        # attribute, then it behaves almost exactly like the previous
        # case, except that each <li> subelement (except the optional
        # last entry) must now include a 'name' attribute.
        else:
            try:
                name = None
                if attr.has_key('name'):
                    name = attr['name']
                # Get the list of <li> elemnents
                listitems = []
                for e in elem[2:]:
                    if e[0] == 'li':
                        listitems.append(e)
                # if listitems is empty, return the empty string
                if len(listitems) == 0:
                    return ""
                # iterate through the list looking for a condition that
                # matches.
                foundMatch = False
                for li in listitems:
                    try:
                        liAttr = li[1]
                        # if this is the last list item, it's allowed
                        # to have no attributes.  We just skip it for now.
                        if len(liAttr.keys()) == 0 and li == listitems[-1]:
                            continue
                        # get the name of the predicate to test
                        liName = name
                        if liName == None:
                            liName = liAttr['name']
                        # get the value to check against
                        liValue = liAttr['value']
                        # do the test
                        if self.getPredicate(liName, sessionID) == liValue:
                            foundMatch = True
                            response += self._processElement(li,sessionID)
                            break
                    except:
                        # No attributes, no name/value attributes, no
                        # such predicate/session, or processing error.
                        if self._verboseMode: print "Something amiss -- skipping listitem", li
                        raise
                if not foundMatch:
                    # Check the last element of listitems.  If it has
                    # no 'name' or 'value' attribute, process it.
                    try:
                        li = listitems[-1]
                        liAttr = li[1]
                        if not (liAttr.has_key('name') or liAttr.has_key('value')):
                            response += self._processElement(li, sessionID)
                    except:
                        # listitems was empty, no attributes, missing
                        # name/value attributes, or processing error.
                        if self._verboseMode: print "error in default listitem"
                        raise
            except:
                # Some other catastrophic cataclysm
                if self._verboseMode: print "catastrophic condition failure"
                raise
        return response
        
    # date
    def _processDate(self, elem, sessionID):
        # Date elements resolve to the current date and time.  There
        # doesn't seem to be any dictated format for the response,
        # so I go with whatever's simplest.
        return time.asctime()

    # formal
    def _processFormal(self, elem, sessionID):
        # Formal elements process their contents and then capitalize the
        # first letter of each word.
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return string.capwords(response)

    # gender
    def _processGender(self,elem, sessionID):
        # Gender elements process their contents, and then swap the gender
        # of any third-person singular pronouns in the result.
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        # Run the results through the gender subber.
        return self._subbers['gender'].sub(response)

    # get
    def _processGet(self, elem, sessionID):
        # Get elements return the value of a predicate from the specified
        # session.  The predicate to get is specified by the 'name'
        # attribute of the element.  Any contents of the element are ignored.
        return self.getPredicate(elem[1]['name'], sessionID)

    # gossip
    def _processGossip(self, elem, sessionID):
        # Gossip elements are used to capture and store user input in
        # an implementation-defined manner.  I haven't decided how to
        # define my implementation, so right now gossip behaves
        # identically to <think>
        return self._processThink(elem, sessionID)

    # id
    def _processId(self, elem, sessionID):
        # Id elements are supposed to return some sort of unique "user id".
        # I choose to return the sessionID, which is the closest thing to
        # a user id that I've got.
        return sessionID

    # input
    def _processInput(self, elem, sessionID):
        # Input elements return an entry from the input history for a
        # given session.  The optional 'index' attribute specifies how
        # far back to look (1 means the last input, 2 is the one
        # before that, and so on).  The contents of the element (there
        # shouldn't be any) are ignored.
        inputHistory = self.getPredicate(self._inputHistory, sessionID)
        try: index = int(elem[1]['index'])
        except: index = 1
        try: return inputHistory[-index]
        except IndexError:
            if self._verboseMode: print "No such index", index, "while processing <input> element."
            return ""

    # javascript
    def _processJavascript(self, elem, sessionID):
        # Javascript elements process their contents, and then run the
        # results through a server-side Javascript interpreter to compute
        # the final response.  Implementations are not required to provide
        # an actual Javascript interpreter, and right now PyAIML doesn't;
        # <javascript> elements behave identically to <think> elements
        # (their contents are processed, and the empty string is returned).
        return self._processThink(elem, sessionID)
    
    # learn
    def _processLearn(self, elem, sessionID):
        # Learn elements contain one piece of data: an element which
        # resolves to a filename for the bot to learn.
        filename = ""
        for e in elem[2:]:
            filename += self._processElement(e, sessionID)
        self.learn(filename)
        return ""

    # li
    def _processLi(self,elem, sessionID):
        # Li (list item) elements are just containers used by <random>
        # and <condition> tags.  Their contents are processed and
        # returned.
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return response

    # lowercase
    def _processLowercase(self,elem, sessionID):
        # Lowercase elements process their contents, and return the results
        # in all lower-case.
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return string.lower(response)

    # person
    def _processPerson(self,elem, sessionID):
        # Person elements process their contents, and then convert all
        # pronouns from 1st person to 2nd person, and vice versa.
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        # An atomic <person/> tag, is a shortcut for <person><star/><person>.
        if len(elem[2:]) == 0:
            response = self._processElement(['star',{}], sessionID)    
        # run it through the 'person' subber
        return self._subbers['person'].sub(response)

    # person2
    def _processPerson2(self,elem, sessionID):
        # Person2 elements process their contents, and then convert all
        # pronouns from 1st person to 3nd person, and vice versa.
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        # An atomic <person2/> tag, is a shortcut for <person><star/><person>.
        if len(elem[2:]) == 0:
            response = self._processElement(['star',{}], sessionID)
        # run it through the 'person2' subber
        return self._subbers['person2'].sub(response)
        
    # random
    def _processRandom(self, elem, sessionID):
        # Random elements contain one or more <li> elements.  The
        # interpreter chooses one of them randomly, processes it, and
        # returns the result. Only the selected <li> element is
        # processed.  Non-<li> subelements are ignored.
        listitems = []
        for e in elem[2:]:
            if e[0] == 'li':
                listitems.append(e)
                
        # select and process a random listitem.
        random.shuffle(listitems)
        try:
            return self._processElement(listitems[0], sessionID)
        except IndexError: # listitems is empty
            return ""

    # sentence
    def _processSentence(self,elem, sessionID):
        # Sentence elements capitalizes the first letter of the first
        # word of its contents.
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        try:
            response = response.strip()
            words = string.split(response, " ", 1)
            words[0] = string.capitalize(words[0])
            response = string.join(words)
            return response
        except IndexError: # response was empty
            return ""

    # set
    def _processSet(self, elem, sessionID):
        # Set elements processes its contents and assigns the results to
        # a predicate in the specified session.  The predicate to set
        # is specified by the required 'name' attribute of the element.
        # The contents of the element are also returned.
        value = ""
        for e in elem[2:]:
            value += self._processElement(e, sessionID)
        self.setPredicate(elem[1]['name'], value, sessionID)    
        return value

    # size
    def _processSize(self,elem, sessionID):
        # Size elements return the number of categories learned.
        return str(self.numCategories())

    # sr
    def _processSr(self,elem,sessionID):
        # <sr/> is a shortcut for <srai><star/></srai>.  So basically, we
        # compute the <star/> string, and then respond to it.
        star = self._processElement(['star',{}], sessionID)
        response = self._respond(star, sessionID)
        return response

    # srai
    def _processSrai(self,elem, sessionID):
        # Srai elements recursively return the response generated by
        # their contents, which must resolve to a valid AIML pattern.
        newInput = ""
        for e in elem[2:]:
            newInput += self._processElement(e, sessionID)
        return self._respond(newInput, sessionID)

    # star
    def _processStar(self, elem, sessionID):
        # Star elements return the text fragment matched by the "*" character
        # in the input pattern.  For example, if the input "Hello Tom Smith,
        # how are you?" matched the pattern "HELLO * HOW ARE YOU", then a
        # <star/> tag in the template would evaluate to "Tom Smith".
        # There is an optional "index" attribute, which specifies which
        # star to expand.  However, since AIML patterns are only allowed
        # to have one * each, only an index of 1 currently makes sense.
        try: index = int(elem[1]['index'])
        except KeyError: index = 1
        if index > 1:
            if self._verboseMode: print "WARNING: index>1 has no meaning in <star> tags"
            return ""
        # fetch the user's last input
        inputStack = self.getPredicate(self._inputStack, sessionID)
        input = self._subbers['normal'].sub(inputStack[-1])
        # fetch the Kernel's last response (for 'that' context)
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        try: that = self._subbers['normal'].sub(outputHistory[-1])
        except: that = "" # there might not be any output yet
        topic = self.getPredicate("topic", sessionID)
        response = self._brain.star("star", input, that, topic)
        return response
    
    # system
    def _processSystem(self,elem, sessionID):
        # System elements cause a command to be executed. If the optional
        # 'mode' attribute is set to "async", the command is run in
        # the background and its output is ignored.  If mode is "sync"
        # (the default), the process is executed, and the interpreter
        # blocks until it exits.  In this case, the element returns any
        # output of the command.

        # determine the mode
        syncMode = True
        try:
            attr = elem[1]
            if attr['mode'] == 'async':
                syncMode = False
        except:
            pass # keep the default

        # build up the command string
        command = ""
        for e in elem[2:]:
            command += self._processElement(e, sessionID)

        # execute the command.
        response = ""
        if syncMode:
            out = os.popen(command)
            for line in out:
                response += line
            response = string.join(response.splitlines())
        else:
            # known issue: Win32 Python doesn't support the
            # os.spawn*p* functions, so under Windows, command must be
            # an absolute or relative path. This SUCKS.  Hope it gets
            # fixed soon.
            cmdlist = string.split(command)
            try:
                pid = os.spawnvpe(os.P_NOWAIT, cmdlist[0], cmdlist, os.environ)
            except AttributeError:
                pid = os.spawnve(os.P_NOWAIT, cmdlist[0], cmdlist, os.environ)
        return response

    # template
    def _processTemplate(self,elem, sessionID):
        # Template elements are root nodes.  They process their
        # contents and return the results.
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return response

    # text
    def _processText(self,elem, sessionID):
        # Text elements are simple wrappers around raw text strings. They
        # have no attributes, and cannot contain other elements in their
        # contents -- instead, they contain a single text string, which
        # is returned immediately.
        try: elem[2] + ""
        except TypeError: raise TypeError, "Text element contents are not text"
        return elem[2]

    # that
    def _processThat(self,elem, sessionID):
        # That elements (inside templates) are the output equivilant of
        # <input> elements; they return one of the Kernel's previous
        # responses, as specified by the optional 'index' attribute.
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        index = 1
        try:
            # According to the AIML spec, the optional index attribute
            # can either have the form "x" or "x,y". x refers to how
            # far back in the output history to go.  y refers to which
            # sentence of the specified response to return.
            index = int(elem[1]['index'].split(',')[0])
        except:
            pass
        try: return outputHistory[-index]
        except IndexError:
            if self._verboseMode: print "No such index", index, "while processing <that> element."
            return ""

    # thatstar
    def _processThatstar(self, elem, sessionID):
        # Thatstar elements are similar to star elements, except that where <star/>
        # returns the portion of the input pattern that was matched by a *,
        # <thatstar/> returns the portion of the "that" pattern that was
        # matched by a *.
        try: index = int(elem[1]['index'])
        except KeyError: index = 1
        if index > 1:
            if self._verboseMode: print "WARNING: index>1 has no meaning in <thatstar> tags"
            return ""
        # fetch the user's last input
        inputStack = self.getPredicate(self._inputStack, sessionID)
        input = self._subbers['normal'].sub(inputStack[-1])
        # fetch the Kernel's last response (for 'that' context)
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        try: that = self._subbers['normal'].sub(outputHistory[-1])
        except: that = "" # there might not be any output yet
        topic = self.getPredicate("topic", sessionID)
        response = self._brain.star("thatstar", input, that, topic)
        return response

    # think
    def _processThink(self,elem, sessionID):
        # Think elements process their sub-elements, and then discard the
        # output. We can't skip the processing, because it could have
        # side effects (which is the whole point of the <think> tag in
        # the first place).
        for e in elem[2:]:
            self._processElement(e, sessionID)
        return ""

    # topicstar
    def _processTopicstar(self, elem, sessionID):
        # Topicstar elements are similar to star elements, except that where <star/>
        # returns the portion of the input pattern that was matched by a *,
        # <topicstar/> returns the portion of the "topic" pattern that was
        # matched by a *.
        try: index = int(elem[1]['index'])
        except KeyError: index = 1
        if index > 1:
            if self._verboseMode: print "WARNING: index>1 has no meaning in <topicstar> tags"
            return ""
        # fetch the user's last input
        inputStack = self.getPredicate(self._inputStack, sessionID)
        input = self._subbers['normal'].sub(inputStack[-1])
        # fetch the Kernel's last response (for 'that' context)
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        try: that = self._subbers['normal'].sub(outputHistory[-1])
        except: that = "" # there might not be any output yet
        topic = self.getPredicate("topic", sessionID)
        response = self._brain.star("topicstar", input, that, topic)
        return response

    # uppercase
    def _processUppercase(self,elem, sessionID):
        # Uppercase elements process their contents, and return the results
        # in all caps.
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return string.upper(response)

    # version
    def _processVersion(self,elem, sessionID):
        # Version elements resolve to the current interpreter version.
        # Any sub-elements are ignored.
        return self.version()


##################################################
### Self-test functions follow                 ###
##################################################
def _testTag(kern, tag, input, outputList):
    """
    Tests 'tag' by feeding the Kernel 'input'.  If the result matches any of
    the strings in 'outputList', the test passes.
    """
    global _numTests, _numPassed
    _numTests += 1
    print "Testing <" + tag + ">:",
    response = kern.respond(input)
    if response in outputList:
        print "PASSED"
        _numPassed += 1
        return True
    else:
        print "FAILED (response: '%s')" % response
        return False

if __name__ == "__main__":
    # Run some self-tests
    k = Kernel()
    k.bootstrap(learnFiles="self-test.aiml")

    global _numTests, _numPassed
    _numTests = 0
    _numPassed = 0

    _testTag(k, 'bot', 'test bot', ["My name is Nameless"])

    k.setPredicate('gender', 'male')
    _testTag(k, 'condition test #1', 'test condition name value', ['You are handsome'])
    k.setPredicate('gender', 'female')
    _testTag(k, 'condition test #2', 'test condition name value', [''])
    _testTag(k, 'condition test #3', 'test condition name', ['You are beautiful'])
    k.setPredicate('gender', 'robot')
    _testTag(k, 'condition test #4', 'test condition name', ['You are genderless'])
    _testTag(k, 'condition test #5', 'test condition', ['You are genderless'])
    k.setPredicate('gender', 'male')
    _testTag(k, 'condition test #6', 'test condition', ['You are handsome'])

    # the date test will occasionally fail if the original and "test"
    # times cross a second boundary.  There's no good way to avoid
    # this problem and still do a meaningful test, so we simply
    # provide a friendly message to be printed if the test fails.
    date_warning = """
    NOTE: the <date> test will occasionally report failure even if it
    succeeds.  So long as the response looks like a date/time string,
    there's nothing to worry about.
    """
    if not _testTag(k, 'date', 'test date', ["The date is %s" % time.asctime()]):
        print date_warning
    
    _testTag(k, 'formal', 'test formal', ["Formal Test Passed"])
    _testTag(k, 'gender', 'test gender', ["He'd told her he heard that her hernia is history"])
    _testTag(k, 'get/set', 'test get and set', ["I like cheese.  My favorite food is cheese"])
    _testTag(k, 'gossip', 'test gossip', ["Gossip is not yet implemented"])
    _testTag(k, 'id', 'test id', ["Your id is _global"])
    _testTag(k, 'input', 'test input', ['You just said: test input'])
    _testTag(k, 'javascript', 'test javascript', ["Javascript is not yet implemented"])
    _testTag(k, 'lowercase', 'test lowercase', ["The Last Word Should Be lowercase"])
    _testTag(k, 'person', 'test person', ['HE think i knows that my actions threaten him and his.'])
    _testTag(k, 'person2', 'test person2', ['YOU think me know that my actions threaten you and yours.'])
    _testTag(k, 'person2 (no contents)', 'test person2 I Love Lucy', ['YOU Love Lucy'])
    _testTag(k, 'random', 'test random', ["response #1", "response #2", "response #3"])
    _testTag(k, 'sentence', "test sentence", ["My first letter should be capitalized."])
    _testTag(k, 'size', "test size", ["I've learned %d categories" % k.numCategories()])
    _testTag(k, 'sr', "test sr test srai", ["srai results: srai test passed"])
    _testTag(k, 'sr nested', "test nested sr test srai", ["srai results: srai test passed"])
    _testTag(k, 'srai', "test srai", ["srai test passed"])
    _testTag(k, 'star test #1', 'You should test star begin', ['Begin star matched: You should']) 
    _testTag(k, 'star test #2', 'test star creamy goodness middle', ['Middle star matched: creamy goodness'])
    _testTag(k, 'star test #3', 'test star end the credits roll', ['End star matched: the credits roll'])
    _testTag(k, 'system mode="sync"', "test system", ["The system says hello!"])
    _testTag(k, 'that test #1', "test that", ["I just said: The system says hello!"])
    _testTag(k, 'that test #2', "test that", ["I have already answered this question"])
    _testTag(k, 'thatstar test #1', "test thatstar", ["I say beans"])
    _testTag(k, 'thatstar test #2', "test thatstar", ["I just said \"beans\""])
    _testTag(k, 'think', "test think", [""])
    k.setPredicate("topic", "fruit")
    _testTag(k, 'topic', "test topic", ["We were discussing apples and oranges"]) 
    k.setPredicate("topic", "Soylent Green")
    _testTag(k, 'topicstar', 'test topicstar', ["Solyent Green is made of people!"])
    _testTag(k, 'uppercase', 'test uppercase', ["The Last Word Should Be UPPERCASE"])
    _testTag(k, 'version', 'test version', ["PyAIML is version %s" % k.version()])

    # Report test results
    print "--------------------"
    if _numTests == _numPassed:
        print "%d of %d tests passed!" % (_numPassed, _numTests)
    else:
        print "%d of %d tests passed (see above for detailed errors)" % (_numPassed, _numTests)

    # Run an interactive interpreter
    #print "\nEntering interactive mode (ctrl-c to exit)"
    #while True: print k.respond(raw_input("> "))

    k.__del__()
    try:
        os.remove("sessions/_global.db")
        os.rmdir("sessions")
    except OSError:
        pass