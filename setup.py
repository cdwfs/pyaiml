# Command to build:
from distutils.core import setup
import glob

package_prefix = "Lib/site-packages/aiml"

setup(name="PyAIML",
    version="0.4",
    author="Cort Stratton",
    author_email="cort@users.sourceforge.net",
    description="Python AIML Interpreter",
    url="http://pyaiml.sourceforge.net/",
    packages=["aiml"],
    data_files=[
        (package_prefix, glob.glob("aiml/self-test.aiml")),
        (package_prefix, glob.glob("*.txt")),
    ],
)
