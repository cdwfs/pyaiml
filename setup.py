# Command to build:
from distutils.core import setup
import glob

setup(name="PyAIML",
    version="0.1",
    author="Cort Stratton",
    author_email="cort@users.sourceforge.net",
    description="Python AIML Interpreter",
    url="http://pyaiml.sourceforge.net/",
    packages=["aiml"],
    data_files=[
        ("aiml", glob.glob("aiml\\self-test.aiml")),
        (".", glob.glob("*.txt")),
        #("standard", glob.glob("standard\\*.aiml")),
        #(".", ("j-alice.ini", "std-startup.xml", "README.txt", "substitutions.xml", "my-howie.aiml", "howie.ini")),	  
    ],
)
