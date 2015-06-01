"""
Python AIML Validator, v1.1
Author: Cort Stratton (cort@cortstratton.org)

Usage:
    aimlvalidate.py file1.aiml [file2.aiml ...]
"""

# Revision history:
#
# 1.0.1: Redirected stderr to stdout
# 1.0: Initial release

import aiml
import glob
import sys
import xml.sax

if __name__ == "__main__":
    # Need input file(s)!
    if len(sys.argv) < 2:
        print __doc__
        sys.exit(2)

    # AimlParser prints its errors to stderr; we redirect stderr to stdout.
    sys.stderr = sys.stdout

    # Iterate over input files    
    validCount = 0
    docCount = 0
    for arg in sys.argv[1:]:
        # Input files can contain wildcards; iterate over matches
        for f in glob.glob(arg):
            parser = xml.sax.make_parser(["aiml.AimlParser"])
            handler = parser.getContentHandler()
            docCount += 1
            print "%s:" % f
            try:
                # Attempt to parse the file.
                parser.parse(f)
                # Check the number of parse errors.
                if handler.getNumErrors() == 0:    
                    validCount += 1
                    print "PASSED\n"
                else:
                    print "FAILED\n"
            except xml.sax.SAXParseException, msg:
                # These errors occur if the document does not contain
                # well-formed XML (e.g. open or unbalanced tags).  If
                # they occur, parsing the whole document is aborted
                # immediately.
                print "FATAL ERROR: %s\n" % msg
                
    # Print final results
    print "%d out of %d documents are AIML 1.0.1 compliant." % (validCount, docCount)
    if docCount == validCount:
        print "Congratulations!"
    else:
        print """For help resolving syntax errors, refer to the AIML 1.0.1 specification
available on the web at: http://alicebot.org/TR/2001/WD-aiml"""
