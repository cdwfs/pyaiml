"""
This file contains the public interface to the aiml module.
"""
import DefaultSubs
from LearnHandler import LearnHandler
from PatternMgr import PatternMgr
from WordSub import WordSub

from ConfigParser import RawConfigParser
import os
import random
import re
import string
import time
import xml.sax


class Kernel:
    # module constants
    _globalSessionID = 0

    def __init__(self, ):
        self._verboseMode = True
        self._version = "0.1"
        self._brain = PatternMgr()

        # set up the sessions        
        self._sessions = {}        
        self._addSession(self._globalSessionID)

        # set up the word substitutors (subbers):
        self._subbers = {}
        self._subbers['gender'] = WordSub(DefaultSubs.defaultGender)
        self._subbers['person'] = WordSub(DefaultSubs.defaultPerson)
        self._subbers['person2'] = WordSub(DefaultSubs.defaultPerson2)
        self._subbers['normal'] = WordSub(DefaultSubs.defaultNormal)
        
        # set up the atom processors
        self._atomProcessors = {
            "condition":    self._processCondition,
            "date":         self._processDate,
            "formal":       self._processFormal,
            "gender":       self._processGender,
            "get":          self._processGet,
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
            "srai":         self._processSrai,
            "system":       self._processSystem,
            "template":     self._processTemplate,
            "think":        self._processThink,
            "uppercase":    self._processUppercase,
            "version":      self._processVersion,
        }

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
            print self.respond(cmd)
            
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
        try:
            return self._sessions[sessionID][name]
        except:
            # no such session or predicate
            if self._verboseMode: print "No such predicate", name, "in session", sessionID
            return ""

    def setPredicate(self, name, value, sessionID = _globalSessionID):
        "Sets the value of the predicate 'name' in the specified session."
        try:
            self._sessions[sessionID][name] = value
        except:
            # silently fail if no such session exists
            if self._verboseMode: print "WARNING: no such sessionID", sessionID

    def loadSubs(self, filename):
        """Load a substitutions file.  The file must be in the Windows-style INI
format (see the standard ConfigParser module docs for information on
this format).  Each section of the file is loaded into its own substituter."""
        inFile = open(filename)
        parser = RawConfigParser()
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

    def _addSession(self, sessionID):
        "Creates a new session with the specified ID string."
        if not self._sessions.has_key(sessionID):
            self._sessions[sessionID] = {}
    def _deleteSession(self, sessionID):
        "Deletes the specified session."
        if self._sessions.has_key(sessionID):
            _sessions.pop(sessionID)

    def learn(self, filename):
        "Loads and learns the contents of the specified AIML file."
        if self._verboseMode: print "Loading %s..." % filename,
        start = time.clock()
        # Load and parse the AIML file
        handler = LearnHandler()
        xml.sax.parse(filename, handler)
        
        # store the pattern/template pairs in the PatternMgr.
        for key,tem in handler.categories.items():
            pat,that = key
            self._brain.add(pat, that, tem)

        if self._verboseMode:
            print "done (%.2f seconds)" % (time.clock() - start)

    def respond(self, input, sessionID = _globalSessionID):
        "Returns the Kernel's response to the input string."
        if len(input) == 0:
            return ""
        
        # Add the session, if it doesn't already exist
        self._addSession(sessionID)

        # run the input through the 'normal' subber
        subbedInput = self._subbers['normal'].sub(input)
        
        # Fetch the interpretable atom for the user's input
        atom = self._brain.match(subbedInput)
        if atom is None:
            if self._verboseMode: print "No match found for input."
            return ""

        # Process the atom into a response string.
        return self._processAtom(atom, sessionID).strip()

    def _processAtom(self,atom, sessionID):
        # The first element of the 'atom' list is a
        # string describing the type of the atom (== the name of
        # the XML tag).  The second element is a dictionary
        # containing attributes passed to the XML tag.  Any
        # remaining elements are atom-specific, and should be
        # treated as additional atoms.
        try:
            handlerFunc = self._atomProcessors[atom[0]]
        except:
            # Oops -- there's no handler function for this atom
            # type!
            if self._verboseMode: print "No handler found for atom", atom[0]
            return ""
        return handlerFunc(atom, sessionID)


    ###################################################
    ### Individual atom-processing functions follow ###
    ###################################################

    # condition
    def _processCondition(self, atom, sessionID):
        # Condition atoms come in three flavors.  Each has different
        # attributes, and each handles their contents differently.
        attr = None
        response = ""
        try: attr = atom[1]
        except:
            if self._verboseMode: print "Missing attributes dict in _processCondition"
            return response
        
        # The simplest case is when the condition tag has both a
        # 'name' and a 'value' attribute.  In this case, if the
        # predicate 'name' has the value 'value', then the contents of
        # the atom are processed and returned.
        if attr.has_key('name') and attr.has_key('value'):
            try:
                val = self.getPredicate(attr['name'], sessionID)
                if val == attr['value']:
                    for a in atom[2:]:
                        response += self._processAtom(a,sessionID)
                    return response
            except:
                if self._verboseMode: print "Something amiss in condition/name/value"
                pass
        
        # If the condition atom has only a 'name' attribute, then its
        # contents are a series of <li> atoms, each of which has a
        # 'value' attribute.  The list is scanned from top to bottom
        # until a match is found.  Optionally, the last <li> atom can
        # have no 'value' attribute, in which case it is processed and
        # returned if no other match is found.
        #
        # If the condition atom has neither a 'name' nor a 'value'
        # attribute, then it behaves almost exactly like the previous
        # case, except that each <li> subatom (except the optional
        # last entry) must now include a 'name' attribute.
        else:
            try:
                name = None
                if attr.has_key('name'):
                    name = attr['name']
                # Get the list of <li> atoms
                listitems = []
                for a in atom[2:]:
                    if a[0] == 'li':
                        listitems.append(a)
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
                            response += self._processAtom(li,sessionID)
                            break
                    except:
                        # No attributes, no name/value attributes, no
                        # such predicate/session, or processing error.
                        if self._verboseMode: print "Something amiss -- skipping listitem", li
                        continue
                if not foundMatch:
                    # Check the last element of listitems.  If it has
                    # no 'name' or 'value' attribute, process it.
                    try:
                        li = listitems[-1]
                        liAttr = li[1]
                        if not (liAttr.has_key('name') or liAttr.has_key('value')):
                            response += self._processAtom(li, sessionID)
                    except:
                        # listitems was empty, no attributes, missing
                        # name/value attributes, or processing error.
                        if self._verboseMode: print "error in default listitem"
                        pass
            except:
                # Some other catastrophic cataclysm
                if self._verboseMode: print "catastrophic condition failure"
                pass
        return response
        
    # date
    def _processDate(self, atom, sessionID):
        # Date atoms resolve to the current date and time.  There
        # doesn't seem to be any dictated format for the response,
        # so I go with whatever's simplest.
        return time.asctime()

    # formal
    def _processFormal(self, atom, sessionID):
        # Formal atoms process their contents and then capitalize the
        # first letter of each word.
        response = ""
        for a in atom[2:]:
            response += self._processAtom(a, sessionID)
        return string.capwords(response)

    # gender
    def _processGender(self,atom, sessionID):
        # Gender atoms process their contents, and then swap the gender
        # of any third-person singular pronouns in the result.
        response = ""
        for a in atom[2:]:
            response += self._processAtom(a, sessionID)
        # Run the results through the gender subber.
        return self._subbers['gender'].sub(response)

    # get
    def _processGet(self, atom, sessionID):
        # Get atoms return the value of a predicate from the specified
        # session.  The predicate to get is specified by the 'name'
        # attribute of the atom.  Any contents of the atom are ignored.
        try:
            return self.getPredicate(atom[1]['name'], sessionID)
        except:
            # no name attribute, no such predicate, or no such session
            return ""

    # learn
    def _processLearn(self, atom, sessionID):
        # Learn atoms contain one piece of data: an atom which
        # resolves to a filename for the bot to learn.
        filename = ""
        for a in atom[2:]:
            filename += self._processAtom(a, sessionID)
        self.learn(filename)
        return ""

    # li
    def _processLi(self,atom, sessionID):
        # Li (list item) tags are just containers used by <random> and
        # <condition> tags.  Their contents are processed and
        # returned.
        response = ""
        for a in atom[2:]:
            response += self._processAtom(a, sessionID)
        return response

    # lowercase
    def _processLowercase(self,atom, sessionID):
        # Lowercase atoms process their contents, and return the results
        # in all lower-case.
        response = ""
        for a in atom[2:]:
            response += self._processAtom(a, sessionID)
        return string.lower(response)

    # person
    def _processPerson(self,atom, sessionID):
        # Person atoms process their contents, and then convert all
        # pronouns from 1st person to 2nd person, and vice versa.
        response = ""
        for a in atom[2:]:
            response += self._processAtom(a, sessionID)
        # run it through the 'person' subber
        return self._subbers['person'].sub(response)

    # person2
    def _processPerson2(self,atom, sessionID):
        # Person2 atoms process their contents, and then convert all
        # pronouns from 1st person to 3nd person, and vice versa.
        # TODO: translate <person2/> into <person2><star/></person2>
        response = ""
        for a in atom[2:]:
            response += self._processAtom(a, sessionID)
        # run it through the 'person2' subber
        return self._subbers['person2'].sub(response)
        
    # random
    def _processRandom(self, atom, sessionID):
        # Random atoms contain one or more <li> atoms.  The
        # interpreter chooses one of them randomly, processes it, and
        # returns the result. Only the selected <li> atom is
        # processed.  Non-<li> subatoms are ignored.
        listitems = []
        for a in atom[2:]:
            if a[0] == 'li':
                listitems.append(a)
                
        # select and process a random listitem.
        random.shuffle(listitems)
        try:
            return self._processAtom(listitems[0], sessionID)
        except IndexError: # listitems is empty
            return ""

    # sentence
    def _processSentence(self,atom, sessionID):
        # Sentence atoms capitalizes the first letter of the first
        # word of its contents.
        response = ""
        for a in atom[2:]:
            response += self._processAtom(a, sessionID)
        try:
            response = response.strip()
            words = string.split(response, " ", 1)
            words[0] = string.capitalize(words[0])
            response = string.join(words)
            return response
        except IndexError: # reponse was empty
            return ""

    # set
    def _processSet(self, atom, sessionID):
        # Set atoms processes its contents and assigns the results to
        # a predicate in the specified session.  The predicate to set
        # is specified by the required 'name' attribute of the atom.
        value = ""
        for a in atom[2:]:
            value += self._processAtom(a, sessionID)

        try:
            self.setPredicate(atom[1]['name'], value, sessionID)
        except:
            # no name attribute, or no such session
            pass
        return ""

    # size
    def _processSize(self,atom, sessionID):
        # Size atoms return the number of categories learned.
        return str(self.numCategories())

    # srai
    def _processSrai(self,atom, sessionID):
        # Srai atoms recursively return the response generated by
        # their contents, which must resolve to a valid AIML pattern.
        newInput = ""
        for a in atom[2:]:
            newInput += self._processAtom(a, sessionID)
        return self.respond(newInput, sessionID)

    # system
    def _processSystem(self,atom, sessionID):
        # System atoms cause a command to be executed. If the optional
        # 'mode' attribute is set to "async", the command is run in
        # the background and its output is ignored.  If mode is "sync"
        # (the default), the process is executed, and the interpreter
        # blocks until it exits.  In this case, the atom returns any
        # output of the command.

        # determine the mode
        syncMode = True
        try:
            attr = atom[1]
            if attr['mode'] == 'async':
                syncMode = False
        except:
            pass # keep the default

        # build up the command string
        command = ""
        for a in atom[2:]:
            command += self._processAtom(a, sessionID)

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
    def _processTemplate(self,atom, sessionID):
        # Template atoms are root nodes.  They process their
        # contents and return the results.
        response = ""
        for a in atom[2:]:
            response += self._processAtom(a, sessionID)
        return response

    # text
    def _processText(self,atom, sessionID):
        # Text atoms are simple wrappers around raw text strings. They
        # have no attributes, and cannot contain other atoms in their
        # contents -- instead, they contain a single text string, which
        # is returned immediately.
        return atom[2]

    # think
    def _processThink(self,atom, sessionID):
        # Think atoms process their sub-atoms, and then discard the
        # output. We can't skip the processing, because it could have
        # side effects (which is the whole point of the <think> tag in
        # the first place).
        for a in atom[2:]:
            self._processAtom(a, sessionID)
        return ""

    # uppercase
    def _processUppercase(self,atom, sessionID):
        # Uppercase atoms process their contents, and return the results
        # in all caps.
        response = ""
        for a in atom[2:]:
            response += self._processAtom(a, sessionID)
        return string.upper(response)

    # version
    def _processVersion(self,atom, sessionID):
        # Version atoms resolve to the current interpreter version.
        # Any sub-atoms are ignored.
        return self._version


##################################################
### Self-test functions follow                 ###
##################################################
def _testTag(kern, tag, input, outputList):
    """
    Tests 'tag' by feeding the Kernel 'input'.  If the result matches any of
    the strings in 'outputList', the test passes.
    """
    print "Testing <" + tag + ">:",
    response = kern.respond(input)
    if response in outputList:
        print "PASSED"
        return True
    else:
        print "FAILED (response: '%s')" % response
        return False

if __name__ == "__main__":
    # Run some self-tests
    k = Kernel()
    k.bootstrap(learnFiles="self-test.aiml")

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
    _testTag(k, 'get/set', 'test get and set', ["My favorite food is cheese"])
    _testTag(k, 'lowercase', 'test lowercase', ["The Last Word Should Be lowercase"])
    _testTag(k, 'person', 'test person', ['YOU think me know that my actions threaten you and yours.'])
    _testTag(k, 'person2', 'test person2', ['HE think i knows that my actions threaten him and his.'])
    _testTag(k, 'random', 'test random', ["response #1", "response #2", "response #3"])
    _testTag(k, 'sentence', "test sentence", ["My first letter should be capitalized."])
    _testTag(k, 'size', "test size", ["I've learned %d categories" % k.numCategories()])
    _testTag(k, 'srai', "test srai", ["srai test passed"])
    _testTag(k, 'system mode="sync"', "test system", ["The system says hello!"])
    _testTag(k, 'think', "test think", [""])
    _testTag(k, 'uppercase', 'test uppercase', ["The Last Word Should Be UPPERCASE"])
    _testTag(k, 'version', 'test version', ["PyAIML is version %s" % k.version()])

    # Run an interactive interpreter
    #print "\nEntering interactive mode (ctrl-c to exit)"
    #while True: print k.respond(raw_input("> "))