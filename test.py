import aiml
import sys

kern = aiml.Kernel()
brainLoaded = False
forceReload = False
while not brainLoaded:
	if forceReload or (len(sys.argv) >= 2 and sys.argv[1] == "reload"):
		kern.bootstrap(learnFiles="std-startup.xml", commands="load aiml b")
		brainLoaded = True
		kern.saveBrain("standard.brn")
	else:
		try:
			kern.bootstrap(brainFile = "standard.brn")
			brainLoaded = True
		except:
			forceReload = True

print "\nINTERACTIVE MODE (ctrl-c to exit)"
while(True):
	input = raw_input("> ")
	print kern.respond(input)
