PyAIML -- The Python AIML Interpreter
author: Cort Stratton (cort@users.sourceforge.net)
web: http://pyaiml.sourceforge.net/
version: 0.1 (pre-alpha)

This is currently pre-alpha software.  Use at your
own risk!

For information on the state of development, including 
the current level of AIML 1.0 compliance, see the
SUPPORTED_TAGS.txt file.

Quick & dirty example (assuming you've downloaded the
"standard" AIML set):

	import aiml

	# The Kernel object is the public interface to
	# the AIML interpreter.
	k = aiml.Kernel()

	# Use the 'learn' method to load the contents
	# of an AIML file into the Kernel.
	k.learn("std-startup.xml")

	# Use the 'respond' method to compute the response
	# to a user's input string.  respond() returns
	# the interpreter's response, which in this case
	# we ignore.
	k.respond("bootstrap")

	# Loop forever, reading user input from the command
	# line and printing responses.
	while True: print k.respond(raw_input("> "))