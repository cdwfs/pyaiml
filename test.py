import aiml
import sys

kern = aiml.Kernel()
if len(sys.argv) >= 2 and sys.argv[1] == "reload":
	kern.bootstrap(learnFile="std-startup.xml", commands=["load aiml b"])
	kern.saveBrain("standard.brn")
else:
	kern.bootstrap(brainFile = "standard.brn")

print "\nINTERACTIVE MODE (ctrl-c to exit)"
while(True):
	input = raw_input("> ")
	print kern.respond(input)
