"""
Python AIML Validator, v1.0
Author: Cort Stratton (cort@users.sourceforge.net)

Usage:
    aimlvalidate.py file1.aiml [file2.aiml ...]
"""

import aiml
import glob
import sys
import xml.sax

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print __doc__
    validCount = 0
    docCount = 0
    for arg in sys.argv[1:]:
        for f in glob.glob(arg):
            handler = aiml.AimlParser()
            docCount += 1
            try:
                print "%s:" % f
                xml.sax.parse(f, handler)
                validCount += 1
                print "PASSED\n"
            except aiml.AimlParserError, msg:
                print "ERROR: %s\n" % msg
            except xml.sax.SAXParseException, msg:
                print "ERROR: %s\n" % msg
    print "%d out of %d documents are AIML 1.0.1 compliant." % (validCount, docCount)
    if docCount == validCount:
        print "Congratulations!"
    else:
        print """For help resolving syntax errors, refer to the AIML 1.0.1 specification
available on the web at: http://alicebot.org/TR/2001/WD-aiml"""