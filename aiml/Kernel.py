"""
This file contains the public interface to the aiml module.
"""
from LearnHandler import *
from PatternMgr import *

import os
import random
import re
import string
import time
import xml.sax


class Kernel:
    # module constants
    __globalSessionID = 0

    def __init__(self, ):
        self.__verboseMode = True
        self.__version = "0.1"
        self.__brain = PatternMgr()
        self.__sessions = {}
        self.__addSession(self.__globalSessionID)
        self.__atomProcessors = {
            "condition":    self.__processCondition,
            "date":         self.__processDate,
            "formal":       self.__processFormal,
            "gender":       self.__processGender,
            "get":          self.__processGet,
            "learn":        self.__processLearn,
            "li":           self.__processLi,
            "lowercase":    self.__processLowercase,
            "random":       self.__processRandom,
            "sentence":     self.__processSentence,
            "set":          self.__processSet,
            "size":         self.__processSize,
            "srai":         self.__processSrai,
            "system":       self.__processSystem,
            "template":     self.__processTemplate,
            "think":        self.__processThink,
            "uppercase":    self.__processUppercase,
            "version":      self.__processVersion,
        }

    def bootstrap(self, brainFile = None, learnFile = None, commands = []):
        """
        Prepares a Kernel object for use.

        If a brainFile argument is provided, the Kernel attempts to
        load the brain at the specified filename.

        If learnFile is provided, the Kernel attempts to load the
        specified AIML file.

        Finally, each of the input strings in the commands list is
        passed to respond().
        """
        start = time.clock()
        if brainFile:
            self.loadBrain(brainFile)
        if learnFile:
            self.learn(learnFile)
        for cmd in commands:
            print self.respond(cmd)
        if self.__verboseMode:
            print "Kernel bootstrap completed in %.2f seconds" % (time.clock() - start)

    def verbose(self, isVerbose = True):
        "Enabled/disables verbose output mode."
        self.__verboseMode = isVerbose

    def version(self):
        "Returns the Kernel's version string."
        return self.__version

    def numCategories(self):
        "Returns the number of categories the Kernel has learned."
        # there's a one-to-one mapping between templates and categories
        return self.__brain.numTemplates()
        
    def resetBrain(self):
        "Erases all of the bot's knowledge."
        del(self.__brain)
        self.__init__()

    def loadBrain(self, filename):
        """
        Attempts to load a previously-saved 'brain' from the
        specified filename.

        NOTE: the current contents of the 'brain' will be discarded!
        """
        if self.__verboseMode: print "Loading brain from %s..." % filename,
        start = time.clock()
        self.__brain.restore(filename)
        if self.__verboseMode:
            end = time.clock() - start
            print "done (%d categories in %.2f seconds)" % (self.__brain.numTemplates(), end)

    def saveBrain(self, filename):
        "Dumps the contents of the bot's brain to a file on disk."
        if self.__verboseMode: print "Saving brain to %s..." % filename,
        start = time.clock()
        self.__brain.save(filename)
        if self.__verboseMode:
            print "done (%.2f seconds)" % (time.clock() - start)

    def getPredicate(self, name, sessionID = __globalSessionID):
        "Retrieves the value of the predicate 'name' from the specified session."
        try:
            return self.__sessions[sessionID][name]
        except:
            # no such session or predicate
            if self.__verboseMode: print "No such predicate", name, "in session", sessionID
            return ""

    def setPredicate(self, name, value, sessionID = __globalSessionID):
        "Sets the value of the predicate 'name' in the specified session."
        try:
            self.__sessions[sessionID][name] = value
        except:
            # silently fail if no such session exists
            if self.__verboseMode: print "WARNING: no such sessionID", sessionID

    def __addSession(self, sessionID):
        "Creates a new session with the specified ID string."
        if not self.__sessions.has_key(sessionID):
            self.__sessions[sessionID] = {}
    def __deleteSession(self, sessionID):
        "Deletes the specified session."
        if self.__sessions.has_key(sessionID):
            _sessions.pop(sessionID)

    def learn(self, filename):
        "Loads and learns the contents of the specified AIML file."
        if self.__verboseMode: print "Loading %s..." % filename,
        start = time.clock()
        # Load and parse the AIML file
        handler = LearnHandler()
        xml.sax.parse(filename, handler)
        
        # store the pattern/template pairs in the PatternMgr.
        for key,tem in handler.categories.items():
            pat,that = key
            self.__brain.add(pat, that, tem)

        if self.__verboseMode:
            print "done (%.2f seconds)" % (time.clock() - start)

    def respond(self, input, sessionID = __globalSessionID):
        # Add the session, if it doesn't already exist
        self.__addSession(sessionID)
        
        # Fetch the interpretable atom for the user's input
        atom = self.__brain.match(input)
        if atom is None:
            if self.__verboseMode: print "No match found for input."
            return ""

        # Process the atom into a response string.
        return self.__processAtom(atom, sessionID).strip()

    def __processAtom(self,atom, sessionID):
        try:
            # if atom is a string, we can just return it as is.
            return atom + ""
        except TypeError:
            # otherwise, atom is a list.  The first element is a
            # string describing the type of the atom (== the name of
            # the XML tag).  The second element is a dictionary
            # containing attributes passed to the XML tag.  Any
            # remaining elements are atom-specific, and should be
            # treated as additional atoms.
            try:
                handlerFunc = self.__atomProcessors[atom[0]]
            except:
                # Oops -- there's no handler function for this atom
                # type!
                if self.__verboseMode: print "No handler found for atom", atom[0]
                return ""
            return handlerFunc(atom, sessionID)


    ###################################################
    ### Individual atom-processing functions follow ###
    ###################################################

    # condition
    def __processCondition(self, atom, sessionID):
        # Condition atoms come in three flavors.  Each has different
        # attributes, and each handles their contents differently.
        attr = None
        response = ""
        try: attr = atom[1]
        except:
            if self.__verboseMode: print "Missing attributes dict in __processCondition"
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
                        response += self.__processAtom(a,sessionID)
                    return response
            except:
                if self.__verboseMode: print "Something amiss in condition/name/value"
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
                    if type(a) == type([]) and a[0] == 'li':
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
                            response += self.__processAtom(li,sessionID)
                            break
                    except:
                        # No attributes, no name/value attributes, no
                        # such predicate/session, or processing error.
                        if self.__verboseMode: print "Something amiss -- skipping listitem", li
                        continue
                if not foundMatch:
                    # Check the last element of listitems.  If it has
                    # no 'name' or 'value' attribute, process it.
                    try:
                        li = listitems[-1]
                        liAttr = li[1]
                        if not (liAttr.has_key('name') or liAttr.has_key('value')):
                            response += self.__processAtom(li, sessionID)
                    except:
                        # listitems was empty, no attributes, missing
                        # name/value attributes, or processing error.
                        if self.__verboseMode: print "error in default listitem"
                        pass
            except:
                # Some other catastrophic cataclysm
                if self.__verboseMode: print "catastrophic condition failure"
                pass
        return response
        
    # date
    def __processDate(self, atom, sessionID):
        # Date atoms resolve to the current date and time.  There
        # doesn't seem to be any dictated format for the response,
        # so I go with whatever's simplest.
        return time.asctime()

    # formal
    def __processFormal(self, atom, sessionID):
        # Formal atoms process their contents and then capitalize the
        # first letter of each word.
        response = ""
        for a in atom[2:]:
            response += self.__processAtom(a, sessionID)
        return string.capwords(response)

    # gender
    def __processGender(self,atom, sessionID):
        # Gender atoms process their contents, and then swap the gender
        # of any third-person singular pronouns in the result.
        response = ""
        for a in atom[2:]:
            response += self.__processAtom(a, sessionID)
        # NOTE: Correctly determining how to replace 'his' ('her' vs.
        # 'hers') and 'her' ('his' vs. 'him') is impossible without a
        # full-on natural language parser.
        subs = {
            "he":"she", "He":"She", "HE":"SHE",
            "him":"her", "Him":"Her", "HIM":"HER",
            "his":"her", "His":"Her", "HIS":"HER",
            "himself":"herself", "Himself":"Herself", "HIMSELF":"HERSELF",
            "she":"he", "She":"He", "SHE":"HE",
            "her":"him", "Her":"Him", "HER":"HIM",
            "hers":"his", "Hers":"His", "HERS":"HIS",
            "herself":"himself", "Herself":"Himself", "HERSELF":"HIMSELF",
        }
        words = string.split(response)
        for i in range(len(words)):
            for k,v in subs.items():
                (words[i],count) = re.subn("^("+k+")(\W|$)", v+"\g<2>", words[i])
                # if we found a match, stop looking for more!
                if count > 0:
                    break
        return string.join(words)

    # get
    def __processGet(self, atom, sessionID):
        # Get atoms return the value of a predicate from the specified
        # session.  The predicate to get is specified by the 'name'
        # attribute of the atom.  Any contents of the atom are ignored.
        try:
            return self.getPredicate(atom[1]['name'], sessionID)
        except:
            # no name attribute, no such predicate, or no such session
            return ""

    # learn
    def __processLearn(self, atom, sessionID):
        # Learn atoms contain one piece of data: an atom which
        # resolves to a filename for the bot to learn.
        filename = ""
        for a in atom[2:]:
            filename += self.__processAtom(a, sessionID)
        self.learn(filename)
        return ""

    # li
    def __processLi(self,atom, sessionID):
        # Li (list item) tags are just containers used by <random> and
        # <condition> tags.  Their contents are processed and
        # returned.
        response = ""
        for a in atom[2:]:
            response += self.__processAtom(a, sessionID)
        return response

    # lowercase
    def __processLowercase(self,atom, sessionID):
        # Lowercase atoms process their contents, and return the results
        # in all lower-case.
        response = ""
        for a in atom[2:]:
            response += self.__processAtom(a, sessionID)
        return string.lower(response)

    # person
    def __processPerson(self,atom, sessionID):
        # Person atoms process their contents, and then convert all
        # pronouns from 1st person to 3rd person, and vice versa.
        response = ""
        for a in atom[2:]:
            response += self.__processAtom(a, sessionID)
        # NOTE: Correctly determining how to replace 'his' ('her' vs.
        # 'hers') and 'her' ('his' vs. 'him') is impossible without a
        # full-on natural language parser.
        subs = {
            # 3rd->1st (masculine)
            "he":"I", "He":"I", "HE":"I",
            "him":"me", "Him":"Me", "HIM":"ME",
            "his":"my", "His":"My", "HIS":"MY",
            "himself":"myself", "Himself":"Myself", "HIMSELF":"MYSELF",
            
            # 3rd->1st (feminine)
            "she":"I", "She":"I", "SHE":"I",
            "her":"me", "Her":"Me", "HER":"ME",
            "hers":"mine", "Hers":"Mine", "HERS":"MINE",
            "herself":"myself", "Herself":"Myself", "HERSELF":"MYSELF",
        }
        words = string.split(response)
        for i in range(len(words)):
            for k,v in subs.items():
                (words[i],count) = re.subn("^("+k+")(\W|$)", v+"\g<2>", words[i])
                # if we found a match, stop looking for more!
                if count > 0:
                    break
        return string.join(words)
        
    # random
    def __processRandom(self, atom, sessionID):
        # Random atoms contain one or more <li> atoms.  The
        # interpreter chooses one of them randomly, processes it, and
        # returns the result. Only the selected <li> atom is
        # processed.  Non-<li> subatoms are ignored.
        listitems = []
        for a in atom[2:]:
            if type(a) == type([]) and a[0] == 'li':
                listitems.append(a)
                
        # select and process a random listitem.
        random.shuffle(listitems)
        try:
            return self.__processAtom(listitems[0], sessionID)
        except IndexError: # listitems is empty
            return ""

    # sentence
    def __processSentence(self,atom, sessionID):
        # Sentence atoms capitalizes the first letter of the first
        # word of its contents.
        response = ""
        for a in atom[2:]:
            response += self.__processAtom(a, sessionID)
        try:
            response = response.strip()
            words = string.split(response, " ", 1)
            words[0] = string.capitalize(words[0])
            response = string.join(words)
            return response
        except IndexError: # reponse was empty
            return ""

    # set
    def __processSet(self, atom, sessionID):
        # Set atoms processes its contents and assigns the results to
        # a predicate in the specified session.  The predicate to set
        # is specified by the required 'name' attribute of the atom.
        value = ""
        for a in atom[2:]:
            value += self.__processAtom(a, sessionID)

        try:
            self.setPredicate(atom[1]['name'], value, sessionID)
        except:
            # no name attribute, or no such session
            pass
        return ""

    # size
    def __processSize(self,atom, sessionID):
        # Size atoms return the number of categories learned.
        return str(self.numCategories())

    # srai
    def __processSrai(self,atom, sessionID):
        # Srai atoms recursively return the response generated by
        # their contents, which must resolve to a valid AIML pattern.
        newInput = ""
        for a in atom[2:]:
            newInput += self.__processAtom(a, sessionID)
        return self.respond(newInput, sessionID)

    # system
    def __processSystem(self,atom, sessionID):
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
            command += self.__processAtom(a, sessionID)

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
    def __processTemplate(self,atom, sessionID):
        # Template atoms are root nodes.  They process their
        # contents and return the results.
        response = ""
        for a in atom[2:]:
            response += self.__processAtom(a, sessionID)
        return response

    # think
    def __processThink(self,atom, sessionID):
        # Think atoms process their sub-atoms, and then discard the
        # output. We can't skip the processing, because it could have
        # side effects (which is the whole point of the <think> tag in
        # the first place).
        for a in atom[2:]:
            self.__processAtom(a, sessionID)
        return ""

    # uppercase
    def __processUppercase(self,atom, sessionID):
        # Uppercase atoms process their contents, and return the results
        # in all caps.
        response = ""
        for a in atom[2:]:
            response += self.__processAtom(a, sessionID)
        return string.upper(response)

    # version
    def __processVersion(self,atom, sessionID):
        # Version atoms resolve to the current interpreter version.
        # Any sub-atoms are ignored.
        return self.__version


##################################################
### Self-test functions follow                 ###
##################################################
def __testTag(kern, tag, input, outputList):
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
    k.bootstrap(learnFile="self-test.aiml")

    k.setPredicate('gender', 'male')
    __testTag(k, 'condition test #1', 'test condition name value', ['You are handsome'])
    k.setPredicate('gender', 'female')
    __testTag(k, 'condition test #2', 'test condition name value', [''])
    __testTag(k, 'condition test #3', 'test condition name', ['You are beautiful'])
    k.setPredicate('gender', 'robot')
    __testTag(k, 'condition test #4', 'test condition name', ['You are genderless'])
    __testTag(k, 'condition test #5', 'test condition', ['You are genderless'])
    k.setPredicate('gender', 'male')
    __testTag(k, 'condition test #6', 'test condition', ['You are handsome'])

    # the date test will occasionally fail if the original and "test"
    # times cross a second boundary.  There's no good way to avoid
    # this problem and still do a meaningful test, so we simply
    # provide a friendly message to be printed if the test fails.
    date_warning = """
    NOTE: the <date> test will occasionally report failure even if it
    succeeds.  So long as the response looks like a date/time string,
    there's nothing to worry about.
    """
    if not __testTag(k, 'date', 'test date', ["The date is %s" % time.asctime()]):
        print date_warning
    
    __testTag(k, 'formal', 'test formal', ["Formal Test Passed"])
    __testTag(k, 'gender', 'test gender', ["He'd told her he heard that her hernia is history"])
    __testTag(k, 'get/set', 'test get and set', ["My favorite food is cheese"])
    __testTag(k, 'lowercase', 'test lowercase', ["The Last Word Should Be lowercase"])
    __testTag(k, 'random', 'test random', ["response #1", "response #2", "response #3"])
    __testTag(k, 'sentence', "test sentence", ["My first letter should be capitalized."])
    __testTag(k, 'size', "test size", ["I've learned %d categories" % k.numCategories()])
    __testTag(k, 'srai', "test srai", ["srai test passed"])
    __testTag(k, 'system mode="sync"', "test system", ["The system says hello!"])
    __testTag(k, 'think', "test think", [""])
    __testTag(k, 'uppercase', 'test uppercase', ["The Last Word Should Be UPPERCASE"])
    __testTag(k, 'version', 'test version', ["PyAIML is version %s" % k.version()])

    # Run an interactive interpreter
    print "\nEntering interactive mode (ctrl-c to exit)"
    while True: print k.respond(raw_input("> "))