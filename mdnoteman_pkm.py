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

def parse_note_file (path, upd_records = None):
    records       = []
    timestamp     = 0
    new_timestamp = 0
    content       = ''
    color         = '#FFFFFF'
    tags          = []
    labels        = []
    links         = []
    prefer_idx    = 0
    color_re      = re.compile(r"^\[color:[a-zA-Z0-9#]+\]\s*$")
    idx_re        = re.compile(r"^\[idx:\d+\]\s*$")
    timestamp_re  = re.compile(r"^@\[\d+\]$")
    label_re      = re.compile(r'^[\s\t]*(@\b[^,|&!~\s|]+\b[\s\t]*)+$')
    tag_re        = re.compile(r'^[\s\t]*(#\b[^,|&!~\s|]+\b[\s\t]*)+$')
    link_re       = re.compile(r'\[\d+\]')

    fulltxt = ''
    is_tags_read       = False
    is_labels_read     = False
    is_color_read      = False
    is_prefer_idx_read = False

    def add_txtnote (timestamp, color, prefer_idx, tags, labels, content):
        txt  = f"@[{timestamp}]\n"
        txt += f"[color:{color}]\n"
        txt += f"[idx:{prefer_idx}]\n"
        if len(tags) > 0:
            txt += '#' + ' #'.join(tags) + "\n"
        if len(labels) > 0:
            txt += '@' + ' @'.join(labels) + "\n"
        txt += content + "\n"
        txt += "\n"

        return txt

    #print (path)
    if os.path.isfile (path):
        f = open (path, 'r')
        for line in f:
            #print (line)
            if timestamp_re.match(line):
                if content != '' or len(labels) > 0 or len(tags) > 0:
                    new_timestamp = int(line.strip()[2:-1])
                    content = content.rstrip ('\n\t ')

                    if upd_records is not None:
                        if timestamp in upd_records:
                            if upd_records[timestamp][1]: # if not deleted
                                rec = upd_records [timestamp][0]
                                fulltxt += add_txtnote (rec['timestamp'], rec['color'], rec['prefer_idx'], rec['tags'], rec['labels'], rec['content'])
                            else: # if deleted, no write
                                pass
                            del upd_records [timestamp]
                        else: # not updated, write old note
                            fulltxt += add_txtnote (timestamp, color, prefer_idx, tags, labels, content)
                            #print (fulltxt)
                    else:
                        records.append({'timestamp': timestamp, 'tags': list(set(tags)),
                                        'content': content, 'labels': list(set(labels)),
                                        'links': list(set(links)), 'color': color, 'prefer_idx': prefer_idx})

                    labels     = []
                    links      = []
                    tags       = []
                    color      = 'white'
                    content    = ''
                    prefer_idx = 0
                    is_tags_read       = False
                    is_labels_read     = False
                    is_color_read      = False
                    is_prefer_idx_read = False
                    timestamp          = new_timestamp
                else:
                    timestamp = int(line.strip()[2:-1])
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

            if not is_prefer_idx_read:
                if idx_re.match(line):
                    prefer_idx = int(line.strip()[5:-1])
                    #print (color)
                    is_prefer_idx_read = True
                    continue

            if upd_records is None:
                links.extend (link_re.findall (line))

            content += line

        f.close()

    if timestamp != 0:
        content = content.rstrip ('\n\t ')

        if upd_records is not None:
            if timestamp in upd_records:
                if upd_records[timestamp][1]: # if not deleted
                    rec = upd_records [timestamp][0]
                    fulltxt += add_txtnote (rec['timestamp'], rec['color'], rec['prefer_idx'], rec['tags'], rec['labels'], rec['content'])
                else: # if deleted, no write
                    pass
                del upd_records [timestamp]
            else: # not updated, write old note
                fulltxt += add_txtnote (timestamp, color, prefer_idx, tags, labels, content)
            #print (fulltxt)
        else:
            records.append({'timestamp': timestamp, 'tags': list(set(tags)),
                            'content': content, 'labels': list(set(labels)),
                            'links': list(set(links)), 'color': color, 'prefer_idx': prefer_idx})


    # Write remaining updated notes
    if upd_records is not None:
        for timestamp, note in upd_records.items():
            if upd_records[timestamp][1]: # if not deleted
                rec = upd_records [timestamp][0]
                fulltxt += add_txtnote (rec['timestamp'], rec['color'], rec['prefer_idx'], rec['tags'], rec['labels'], rec['content'])

        if os.path.isfile (path) and (fulltxt == ''): #if all notes were deleted, rm file
            os.remove (path)
        else:
            f = open (path, 'w')
            f.write(fulltxt)
            f.close ()

    return records

@dataclass
class Note:
    tags      : Set[str] = field (default_factory = lambda: {})
    labels    : Set[str] = field (default_factory = lambda: {})
    content   : str = ''
    timestamp : int = 0
    links     : List[int] = field (default_factory = lambda: [])
    color     : str = 'white'
    prefer_idx: int = 0 # start from 1, 0 == undefined
    dirty     : bool = False
    deleted   : bool = False

    @property
    def simple_context (self):
        _content = "---\n\n"
        _content += ' '.join(['#' + tag for tag in self.tags]) + "\n\n"
        _content += ' '.join(['@' + lbl for lbl in self.labels])
        return _content

    @property
    def simple_content (self):
        _content = ''
        if self.content != '':
            _content += f"{self.content}\n\n"
        return _content

    @property
    def dict (self):
        return {'timestamp': self.timestamp, 'tags': self.tags.copy(), 'labels': self.labels.copy(),
                'content': self.content, 'links': self.links.copy(), 'color': self.color, 'prefer_idx': self.prefer_idx}

    def set (self, note_info, set_dirty = False):
        if isinstance (note_info, dict):
            for k in note_info:
                setattr (self, k, note_info [k])
        else:
            self.set (note_info.dict)
        if set_dirty:
            self.set_dirty ()

    def set_dirty (self, delete = False):
        self.dirty   = True
        self.deleted = delete

    def __str__ (self):
        inf = self.dict.copy ()
        inf ['content'] = inf ['content'][:20] + ('...' if len(inf['content']) > 20 else '')
        inf ['dirty'] = self.dirty
        inf ['deleted'] = self.deleted
        return f"{inf}"

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

    @property
    def labels_flatten (self):
        def travel_labels (prefix, lbl_dict):
            lbls = {}
            for k, v in lbl_dict.items():
                prefix_k = prefix + k 
                lbls [prefix_k] = v ['count']
                if v['children']:
                    lbls = lbls | travel_labels (prefix_k + '/', v['children'])
            return lbls

        return travel_labels ('', self.labels)

    def Pull_From_Disk (self):
        '''Fetch notes from disk, override note by version on disk if it was not modified in app
        It returns in-app modified version if conflict'''

        file_hndl   = {}
        filename_re = re.compile(r"\d\d\d\d_\d\d_\d\d\.md")

        for note_file in listdir_nohidden (self.path):
            if filename_re.match (note_file):
                filename = os.path.join (self.path, note_file)
                records  = parse_note_file (filename)
                #print (records)

                for rec in records:
                    fetch_en = True
                    found_idx = self.find_note (rec['timestamp'])
                    #print (f"{rec['timestamp']} - {rec['tags']}")
                    #print (found_idx)
                    if found_idx is not None:
                        if self.notes[found_idx].dirty:
                            self.notes[found_idx].prefer_idx = found_idx + 1
                            if note_file not in file_hndl:
                                file_hndl [note_file] = {}
                            file_hndl [note_file][self.notes[found_idx].timestamp] = (self.notes[found_idx].dict, not self.notes[found_idx].deleted)
                        else:
                            self.update_note (found_idx, rec)
                    else:
                        self.add_note (rec)

        #print (file_hndl)
        print ("Pulled from storage.")
        return file_hndl

    def Sync (self, file_records = dict(), delete_sync = False):
        '''Check and resolve note, tags, labels and index coherency
        It appends in-app modified version of notes'''

        file_hndl = file_records

        i = 0
        l = len (self.notes)
        while i < l:
            note = self.notes[i]
            #print (f"{i}: {note.dict}")
            if note.dirty or (note.prefer_idx != i + 1):
                dt       = datetime.fromtimestamp (note.timestamp)
                filename = dt.strftime('%Y_%m_%d.md')
                #print (f"{note.timestamp} -> {filename}")
                if filename not in file_hndl:
                    file_hndl [filename] = {}
                note.prefer_idx = i + 1
                file_hndl [filename][note.timestamp] = (note.dict, not note.deleted)

                if note.deleted:
                    self.remove_note (i, delete = delete_sync)
                    i += (1 if not delete_sync else 0)
                    if delete_sync:
                        l = len (self.notes)
                else:
                    i += 1

            else:
                i += 1
        print ("Synced notes.")
        return file_hndl

    def Push_To_Disk (self, file_records):
        '''Push modified version of notes to disk'''

        file_hndl = file_records

        for fn, records in file_hndl.items():
            parse_note_file (os.path.join (self.path, fn), records)

        print ("Write-back done.")

    def Refresh (self):
        file_records = self.Pull_From_Disk ()
        #print (file_records)
        #for note in self.notes:
        #    print (note)
        file_records = self.Sync (file_records, delete_sync = True)
        #for note in self.notes:
        #    print (note)
        #print (file_records)
        self.Push_To_Disk (file_records)

    def remove_note (self, idx, delete = False):
        if delete:
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

        return note

    def find_note (self, timestamp):
        for i in range(len(self.notes)):
            if self.notes[i].timestamp == timestamp:
                return i
        return None

    def remove_lbl (self, lbl_dict, lbl):
        #print (lbl)
        if lbl [0] in lbl_dict:
            if lbl_dict[lbl[0]]['count'] > 0:
                lbl_dict[lbl[0]]['count'] -= 1
                if len (lbl) > 1:
                    self.remove_lbl (lbl_dict[lbl[0]]['children'], lbl [1:])
            else:
                del (lbl_dict[lbl[0]])

    def add_lbl (self, lbl_dict, lbl):
        if lbl[0] not in lbl_dict:
            lbl_dict[lbl[0]] = {'count': 1, 'children': {}}
        else:
            lbl_dict[lbl[0]]['count'] += 1
        if len (lbl) > 1:
            self.add_lbl (lbl_dict[lbl[0]]['children'], lbl [1:])

    def update_note (self, note_or_idx, note_info, set_dirty = False):
        if isinstance (note_info, Note):
            rec = note_info.dict
        else:
            rec = note_info

        if isinstance (note_or_idx, Note):
            idx = self.notes.index (note_or_idx)
        else:
            idx = note_or_idx

        self.remove_note (idx, delete = False)

        note = self.notes [idx]
        note.set (rec, set_dirty = set_dirty)

        for t in note.tags:
            if t not in self.tags:
                self.tags [t] = 1
            else:
                self.tags [t] += 1

        for l in note.labels:
            lbl = l.split ('/')
            self.add_lbl (self.labels, lbl)

    def add_note (self, note_info):
        note = Note ()
        note.set (note_info)

        if note.prefer_idx == 0: # undefined
            self.notes.append (note)
        else:
            i = 0
            l = len(self.notes)
            while i < l and self.notes[i].prefer_idx > 0 and self.notes[i].prefer_idx < note.prefer_idx:
                i += 1
            self.notes.insert (i, note)
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
