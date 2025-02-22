#!/usr/bin/env python

import sys
if sys.hexversion < 0x03070000:
    print("!!! This component requires Python version 3.7 at least !!!")
    sys.exit(1)

from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Note:
    tags      : List[str] = field (default_factory = lambda: [])
    labels    : List[str] = field (default_factory = lambda: [])
    title     : str = ''
    content   : str = ''
    timestamp : int = 0

@dataclass
class Notebook:
    tags   : Dict = None
    labels : Dict = None
    path   : str  = None
    notes  : List[Note] = field (default_factory = lambda: [])

    def Refresh (self):
        print (self.path)
