#!/usr/bin/env python

import sys
if sys.hexversion < 0x03070000:
    print("!!! This component requires Python version 3.7 at least !!!")
    sys.exit(1)

from dataclasses import dataclass, field
from typing import List, Dict, Set
import random

@dataclass
class Note:
    tags      : Set[str] = field (default_factory = lambda: {'aaa', 'bbb', 'ccc'})
    labels    : Set[str] = field (default_factory = lambda: {'AAA/A1A1A1', 'BBB'})
    title     : str = 'Test note'
    content   : str = 'Test note'
    name      : str = None
    color     : str = 'WHITE'

    @property
    def simple_context (self):
        _content = "---\n\n"
        _content += f"{' '.join(['\\#' + tag for tag in self.tags])}\n\n"
        _content += f"{'\n\n'.join(['@' + lbl for lbl in self.labels])}"
        return _content
    @property

    def simple_content (self):
        _content = f"# {self.title}\n\n"
        _content += f"{self.content}\n\n"
        return _content

@dataclass
class Notebook:
    tags   : Dict = field (default_factory = lambda: {})
    labels : Dict = field (default_factory = lambda: {})
    #labels : Dict = field (default_factory = lambda: {'A': {'count' : 10, 'children': {}},
    #                                                  'B': {'count' : 5, 'children': {'B1': {'count': 2, 'children': {}},
    #                                                                                  'B2': {'count': 3, 'children': {}}}},
    #                                                  'C': {'count' : 3, 'children': {}}})
    path   : str  = None
    notes  : List[Note] = field (default_factory = lambda: [])

    def Refresh (self):
        print (self.path)

    def add_lbl (self, lbl_dict, lbl):
        if lbl[0] not in lbl_dict:
            lbl_dict[lbl[0]] = {'count': 1, 'children': {}}
        else:
            lbl_dict[lbl[0]]['count'] += 1
        if len (lbl) > 1:
            self.add_lbl (lbl_dict[lbl[0]]['children'], lbl [1:])

    def add_note (self, note):
        self.notes += [note]
        for t in self.notes[-1].tags:
            if t not in self.tags:
                self.tags [t] = 1
            else:
                self.tags [t] += 1

        for l in self.notes[-1].labels:
            lbl = l.split ('/')
            self.add_lbl (self.labels, lbl)

    def Create_random_notes (self, name_prf = '', num = 10):
        for i in range (num):
            note = Note(name = name_prf + str(i), title = f"Test note {i}", content = "Test note " * random.randrange (2, 240, 2))
            self.add_note (note)
