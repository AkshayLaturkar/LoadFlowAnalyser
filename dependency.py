try:
    import gi;
    gi.require_version('Gtk', '3.0');
    print("python gi package found");
except:
    print("python gi package not found");

try:
    from gi.repository import Gtk;
    print("python Gtk package found");
except:
    print("python Gtk package not found");

try:
    import numpy;
    print("python numpy package found");
except:
    print("python numpy package not found");

try:
    import pandas;
    print("python pandas package found");
except:
    print("python pandas package not found");

try:
    import xlrd;
    print("python xlrd package found");
except:
    print("python xlrd package not found");

try:
    from collections import Counter;
    print("python Counter package found");
except:
    print("python Counter package not found");

try: 
    import signal;
    print("python signal package found");
except:
    print("python signal package not found");

try: 
    import shutil;
    print("python shutil package found");
except:
    print("python shutil package not found");

try: 
    import os;
    print("python os package found");
except:
    print("python os package not found");

try: 
    import sys;
    print("python sys package found");
except:
    print("python sys package not found");
