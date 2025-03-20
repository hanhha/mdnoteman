#!/usr/bin/env python

import sys
if sys.hexversion < 0x03070000:
    print("!!! This component requires Python version 3.7 at least !!!")
    sys.exit(1)

from dataclasses import dataclass, field
from typing import List, Dict, Set
import random
import os
import re
from datetime import datetime

def listdir_nohidden (path):
    return list(filter(lambda f: not f.startswith('.'), os.listdir(path)))

def parse_note_file (path):
    records = []
    timestamp = 0
    new_timestamp = 0
    content = ''
    color   = 'white'
    tags    = []
    labels  = []
    links   = []
    color_re     = re.compile(r"^\[color:[a-zA-Z0-9#]+\]\s*$")
    timestamp_re = re.compile(r"^@\[\d+\]$")
    label_re     = re.compile(r'^[\s\t]*(@\b[^,|&!~\s|]+\b[\s\t]*)+$')
    tag_re       = re.compile(r'^[\s\t]*(#\b[^,|&!~\s|]+\b[\s\t]*)+$')
    link_re      = re.compile(r'\[\d+\]')

    f = open (path, 'r')
    is_tags_read    = False
    is_labels_read  = False
    is_color_read   = False

    #print (path)
    for line in f:
        #print (line)
        if timestamp_re.match(line):
            if content != '' or len(labels) > 0 or len(tags) > 0 or len(links) > 0:
                new_timestamp = int(line.strip()[2:-1])
                records.append({'timestamp': timestamp, 'tags': list(set(tags)),
                                'content': content, 'labels': list(set(labels)),
                                'links': list(set(links)), 'color': color})
                labels         = []
                links          = []
                tags           = []
                color          = 'white'
                content        = ''
                is_tags_read   = False
                is_labels_read = False
                is_color_read  = False
                timestamp      = new_timestamp
            else:
                timestamp = int(line.strip()[2:-2])
            continue
        if not is_tags_read:
            if tag_re.match(line):
                for tag in line.split('#'):
                    t = tag.strip().lower()
                    if t != '':
                        tags.append (t)
                is_tags_read = True
                continue
        if not is_labels_read:
            if label_re.match(line):
                for lbl in line.split('@'):
                    l = lbl.strip().lower()
                    if l != '':
                        labels.append (l)
                is_labels_read = True
                continue
        if not is_color_read:
            if color_re.match(line):
                color = line.strip()[7:-1]
                #print (color)
                is_color_read = True
                continue

        links.extend (link_re.findall (line))
        content += line

    if timestamp != 0:
        records.append({'timestamp': timestamp, 'tags': list(set(tags)),
                        'content': content, 'labels': list(set(labels)),
                        'links': list(set(links)), 'color': color})

    f.close()
    return records

@dataclass
class Note:
    tags      : Set[str] = field (default_factory = lambda: {})
    labels    : Set[str] = field (default_factory = lambda: {})
    content   : str = ''
    timestamp : int = 0
    links     : List[int] = field (default_factory = lambda: [])
    color     : str = 'white'
    dirty     : bool = False
    deleted   : bool = False

    @property
    def simple_context (self):
        _content = "---\n\n"
        _content += f"{' '.join(['\\#' + tag for tag in self.tags])}\n\n"
        _content += f"{'\n\n'.join(['@' + lbl for lbl in self.labels])}"
        return _content

    @property
    def simple_content (self):
        _content = ''
        if self.content != '':
            _content += f"{self.content}\n\n"
        return _content

    @property
    def dict (self):
        return {'timestamp': int(self.timestamp), 'tags': self.tags.copy(), 'labels': self.labels.copy(),
                'content': self.content, 'links': self.links.copy(), 'color': self.color}

    def set_dirty (self, delete = False):
        self.dirty   = True
        self.deleted = delete

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

    def Pull_From_Disk (self):
        file_hndl   = {}

        for note in listdir_nohidden (self.path):
            if note[-3:] == '.md':
                filename = os.path.join(self.path, note)
                records  = parse_note_file (filename)
                #print (records)
                file_hndl [filename] = []
                has_update = False

                for rec in records:
                    fetch_en = True
                    found_idx = self.find_note (rec['timestamp'])
                    #print (f"{rec['timestamp']} - {rec['tags']}")
                    #print (found_idx)
                    if found_idx is not None:
                        if self.notes[found_idx].dirty:
                            fetch_en  = False
                            has_update = True
                            file_hndl [filename].append ((self.notes[found_idx].dict, not self.notes[found_idx].deleted))
                        else:
                            self.remove_note (found_idx, synced = True)

                    if fetch_en:
                        file_hndl [filename].append ((rec, True))
                        note = Note(tags = rec['tags'], labels = rec['labels'], content = rec['content'],
                                    timestamp = rec['timestamp'], links = rec['links'], color = rec['color'])
                        self.add_note (note)
                        #print (self.notes[-1].tags)

                if not has_update:
                    del file_hndl [filename]
        #print (file_hndl)
        print ("Pulled from storage.")
        return file_hndl

    def Sync (self, file_records = dict(), delete_sync = False):
        file_hndl = file_records

        i = 0
        l = len (self.notes)
        while i < l:
            note = self.notes[i]
            if note.dirty:
                dt       = datetime.fromtimestamp (note.timestamp)
                filename = dt.strftime('%Y_%m_%d.md')
                if filename not in file_hndl:
                    file_hndl [filename] = []
                file_hndl [filename].append ((note.dict, not note.deleted))

                if note.deleted:
                    self.remove_note (i, synced = delete_sync)
                    l = len (self.notes)
                    i += 1 if not delete_sync else 0
                else:
                    i += 1

            else:
                i += 1
        print ("Synced notes.")
        return file_hndl

    def Push_To_Disk (self, file_records):
        file_hndl = file_records

        for fn, records in file_hndl.items():
            f = open (fn, 'w')
            has_writeback = False
            for rec in records:
                if rec[1]: # if note was not deleted
                    #print (rec[0])
                    txt = f"@[{rec[0]['timestamp']}]\n"
                    txt += f"[color:{rec[0]['color']}]\n"
                    if len(rec[0]['tags']) > 0:
                        txt += '#' + ' #'.join(rec[0]['tags']) + "\n"
                    if len(rec[0]['labels']) > 0:
                        txt += '@' + ' @'.join(rec[0]['labels']) + "\n"
                    texts = rec[0]['content'].split('\n')
                    if texts[-1] == '':
                        del texts[-1]
                    for text in texts:
                        txt += text + "\n"
                    txt += "\n"
                    #print (txt)
                    f.write(txt)
                    has_writeback = True
            f.close ()
            if not has_writeback:
                os.remove (fn)

        print ("Write-back done.")

    def Refresh (self):
        file_records = self.Pull_From_Disk ()
        file_records = self.Sync (file_records, delete_sync = True)
        self.Push_To_Disk (file_records)

    def remove_note (self, idx, synced = False):
        if synced:
            note = self.notes.pop (idx)
        else:
            note = self.notes [idx]

        for t in note.tags:
            if t in self.tags:
                if self.tags[t] > 1:
                    self.tags[t] -= 1
                else:
                    del self.tags[t]
        for lbl in note.labels:
            lbls = lbl.split ('/')
            self.remove_lbl (self.labels, lbls)

    def find_note (self, timestamp):
        for i in range(len(self.notes)):
            if self.notes[i].timestamp == timestamp:
                return i
        return None

    def remove_lbl (self, lbl_dict, lbl):
        if lbl[0] in lbl_dict:
            if lbl_dict[lbl[0]]['count'] > 0:
                lbl_dict[lbl[0]]['count'] -= 1
        if len (lbl) > 1:
            self.remove_lbl (lbl_dict[lbl[0]]['children'], lbl [1:])

    def add_lbl (self, lbl_dict, lbl):
        if lbl[0] not in lbl_dict:
            lbl_dict[lbl[0]] = {'count': 1, 'children': {}}
        else:
            lbl_dict[lbl[0]]['count'] += 1
        if len (lbl) > 1:
            self.add_lbl (lbl_dict[lbl[0]]['children'], lbl [1:])

    def add_note (self, note):
        self.notes.append (note)
        for t in note.tags:
            if t not in self.tags:
                self.tags [t] = 1
            else:
                self.tags [t] += 1

        for l in note.labels:
            lbl = l.split ('/')
            self.add_lbl (self.labels, lbl)

    def Create_random_notes (self, name_prf = '', num = 10):
        for i in range (num):
            note = Note(name = name_prf + str(i), title = f"Test note {i}", content = "Test note " * random.randrange (2, 240, 2))
            self.add_note (note)

if __name__ == '__main__':
    pass
