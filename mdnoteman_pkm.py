#!/usr/bin/env python

import sys
if sys.hexversion < 0x03070000:
    print("!!! This component requires Python version 3.7 at least !!!")
    sys.exit(1)

from dataclasses import dataclass, field
from typing import List, Dict
import random

@dataclass
class Note:
    tags      : List[str] = field (default_factory = lambda: ['aaa', 'bbb', 'ccc'])
    labels    : List[str] = field (default_factory = lambda: ['AAA', 'AAA/A1A1A1'])
    title     : str = 'Test note'
    content   : str = 'Test note'
    name      : str = None
    color     : str = 'WHITE'

    @property
    def simple_content (self):
        _content = f"**{self.title}**  \n"
        _content += f"{self.content}  \n"
        _content += "  \n"
        _content += f"{' '.join(['\# ' + tag for tag in self.tags])}  \n"
        _content += f"{' '.join(['\@ ' + lbl for lbl in self.labels])}  \n"
        return _content

@dataclass
class Notebook:
    tags   : Dict = None
    labels : List[Dict] = field (default_factory = lambda: [{'txt': 'A', 'count' : 10, 'children': None},
                                                            {'txt': 'B', 'count' : 5, 'children': [{'txt': 'B1', 'count': 2, 'children': None},
                                                                                                   {'txt': 'B2', 'count': 3, 'children': None}]},
                                                            {'txt': 'C', 'count' : 3, 'children': None}])
    path   : str  = None
    notes  : List[Note] = field (default_factory = lambda: [])

    def Refresh (self):
        print (self.path)

    def Create_random_notes (self, name_prf = '', num = 10):
        for i in range (num):
            self.notes += [Note(name = name_prf + str(i), content = "Test note " * random.randrange (2, 240, 2))]
