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
from PIL import Image, ImageDraw, ImageFont
import io
from copy import copy
import FreeSimpleGUI as sg
import fsg_extend as esg
import mdnoteman_dsl as dsl
from md2img import Markdown_Ext

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
    link_re       = re.compile(r'\(\d+\)')

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
                    color      = '#FFFFFF'
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
    color     : str = '#FFFFFF'
    prefer_idx: int = 0 # start from 1, 0 == undefined
    dirty     : bool = False
    deleted   : bool = False

    @property
    def simple_context (self):
        _content = "---\n\n"
        _content += ' '.join(['\#' + tag for tag in self.tags]) + "\n\n"
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

    def add_note (self, note_info, set_dirty = False):
        note = Note ()
        note.set (note_info, set_dirty = set_dirty)

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

@dataclass
class NoteCard:
    note: Note = None
    name: str = None
    width: int = 240
    _thumbnail: Image = None
    _thumbnail_bio: io.BytesIO = None

    @property
    def thumbnail (self):
        return self._thumbnail

    @property
    def thumbnail_bio (self):
        return self._thumbnail_bio

    def set_fig (self, fig):
        self.fig = fig

    def init (self, md = None):
        self.update (md)

    def update (self, md):
        ctn       = md.convert_img (self.note.simple_content)
        ctn_h     = 240 if (ctn.size[1] > 240) else ctn.size[1]
        ctx       = md.convert_img (self.note.simple_context)
        ctx_h     = ctx.size [1]
        img = Image.new ("RGBA", (self.width, ctn_h + ctx_h))
        img.paste (ctn, (0, 0))
        img.paste (ctx, (0, ctn_h))
        bio = io.BytesIO ()
        img.save (bio, format = "PNG")
        self._thumbnail = img.copy ()
        self._thumbnail_bio = bio.getvalue ()
        del img

@dataclass
class CardBox:
    cards    : List[NoteCard] = field (default_factory = lambda: [])
    notebook : Notebook = None
    n_cols   : int = 3
    window   : sg.Window = None
    name     : str = ''
    width    : int = 768
    md       : Markdown_Ext = None
    graph    : esg.Graph = None

    def get_note_by_timestamp (self, timestamp):
        for note in self.cards:
            if note.note.timestamp == timestamp:
                return note
        return None

    def scroll_handle (self, event):
        if self.container_scroll_cb:
            self.container_scroll_cb (event)
        return 'break'

    @property
    def layout (self):
        comm_menu = ["",["that","this","there",['Thing1','Thing2',"those"]]]
        note_menu = ["",["Color::fig_color",
                         "Add labels::fig_menu","Add tags::fig_menu", "Delete::fig_menu"]]
        _layout = [(esg.Graph (key = (self.name, "graph"),
                              canvas_size = (self.width, 1), graph_bottom_left = (0, 1), graph_top_right = (self.width, 0),
                               expand_x = True, expand_y = True, enable_events = True, drag_submits = True,
                               comm_right_click_menu = comm_menu, fig_right_click_menu = note_menu))]
        return [_layout]

    @property
    def cards_oi (self):
        """ return cards of interest """
        return self._cards_oi

    def filter (self, query_str = ''):
        changed = False
        if query_str != '':
            l = len (self.cards)
            try:
                dsl.lexer.input (query_str)
                flt = dsl.build_ast (dsl.lexer)
            except ValueError as err:
                print ("Invalid query string %s - Ignored" %(query_str))
                flt = None
            if flt:
                print (flt)
                self._cards_oi = []
                tst_ovrd = False
                for i in range (l):
                    tst = False
                    if not tst_ovrd:
                        try:
                            tst = flt.analyze (tags = self.cards[i].note.tags, labels = self.cards[i].note.labels, ctn = self.cards[i].note.content)
                        except ValueError:
                            print ("Invalid query string %s - Ignored" %(query_str))
                            tst = True
                            tst_ovrd = True
                    if tst_ovrd or tst:
                        self._cards_oi.append (self.cards[i])
                changed = True
        else:
            self._cards_oi = self.cards
            changed = True

        if changed:
            self.refresh_box ()

    def set_notebook (self, nb):
        self.notebook = nb
        self.sync_cards ()

    def sync_cards (self, dirty_only = False):
        print ("Syncing cards to box ...")

        for note in self.notebook.notes:
            if (not dirty_only) or (note.dirty):
                card = NoteCard(note = note)
                card.init (self.md)
                self.add_or_replace (card)

        self.filter ()

        print ("Sync notes to cardbox done.")

    def add_or_replace (self, card):
        l = len(self.cards)
        i = 0
        while i < l:
            if self.cards[i].note.timestamp == card.note.timestamp:
                break
            i += 1

        if i < l:
            if not card.note.deleted:
                ret = self.cards[i]
                self.cards[i] = card
            else:
                self.card.pop (i)
        else:
            if not card.note.deleted:
                self.cards.insert (0, card)

    def erase (self):
        self.window[self.name].set_vscroll_position (0)
        size = self.window[self.name].get_size ()
        h = size[1] - 10
        self.graph.set_size ((self.width, h))
        self.graph.change_coordinates ((0, h), (self.width, 0))
        self.graph.erase()

    def resize (self, width):
        self.width = width
        old_n_cols = self.n_cols
        self.n_cols = self.width // 256

        if self.n_cols != old_n_cols:
            self.refresh_box ()

    def rearrange_box (self):
        N = len (self.cards_oi)

        c = 0
        for n in range (N):
            i = 1
            y = 0
            upper_n = n - i*self.n_cols
            while (upper_n >= 0):
                y += (self.cards_oi[upper_n].thumbnail.size[1] + 16)
                i += 1
                upper_n = n - i*self.n_cols

            w,h = self.cards_oi[n].thumbnail.size
            if y + 16 + h > self.graph.CanvasSize [1]:
                self.graph.set_size ((self.width, y + 16 + h))
                self.graph.change_coordinates ((0, y + 16 + h), (self.width, 0))

            (ox1, oy1), (ox2, oy2) = self.graph.get_bounding_box (self.cards_oi[n].fig[0])
            self.graph.move_figure (self.cards_oi[n].fig[0], c * 256 + 6 - ox1, y + 6 - oy1)
            (ox1, oy1), (ox2, oy2) = self.graph.get_bounding_box (self.cards_oi[n].fig[1])
            self.graph.move_figure (self.cards_oi[n].fig[1], c * 256 + 8 - ox1, y + 8 - oy1)
            c = 0 if (c + 1 == self.n_cols) else c + 1

        self.window [self.name].widget.update ()
        self.window [self.name].contents_changed ()
        self.window [self.name].expand (expand_row = True)

    def refresh_box (self):
        self.n_cols = self.width // 256
        N = len (self.cards_oi)

        if self.window:
            self.erase ()

            c = 0
            for n in range (N):
                i = 1
                y = 0
                upper_n = n - i*self.n_cols
                while (upper_n >= 0):
                    y += (self.cards_oi[upper_n].thumbnail.size[1] + 16)
                    i += 1
                    upper_n = n - i*self.n_cols

                w,h = self.cards_oi[n].thumbnail.size
                if y + 16 + h > self.graph.CanvasSize [1]:
                    self.graph.set_size ((self.width, y + 16 + h))
                    self.graph.change_coordinates ((0, y + 16 + h), (self.width, 0))

                bg  = self.graph.draw_rectangle (top_left = (c * 256 + 6, y + 6),
                                                 bottom_right = (c * 256 + 8 + w + 2, y + 8 + h + 2),
                                                 line_color = 'black', line_width = 1,
                                                 fill_color = self.cards_oi[n].note.color)
                fig = self.graph.draw_image (data = self.cards_oi[n].thumbnail_bio, location = (c * 256 + 8, y + 8))
                self.cards_oi[n].set_fig ((bg, fig))
                c = 0 if (c + 1 == self.n_cols) else c + 1

            self.window [self.name].widget.update ()
            self.window [self.name].contents_changed ()
            self.window [self.name].expand (expand_row = True)

    def find_note_at_fig (self, fig):
        for card in self.cards_oi:
            if card.fig == fig:
                return card.note
        return None

    def swap (self, fig1, fig2, always_refresh = False):
        #print (f"{fig1} <-> {fig2}")

        if fig1 != fig2:
            fig1_found = fig2_found = False
            fig1_idx = fig2_idx = 0

            for i in range (len (self.cards_oi)):
                if self.cards_oi[i].fig == fig1:
                    fig1_idx = i
                    fig1_found = True
                    if fig1_found and fig2_found:
                        break
                    else:
                        continue
                if self.cards_oi[i].fig == fig2:
                    fig2_idx = i
                    fig2_found = True
                    if fig1_found and fig2_found:
                        break
                    else:
                        continue

            if fig1_found and fig2_found:
                note1_idx = self.cards_oi[fig1_idx].note.prefer_idx - 1
                note2_idx = self.cards_oi[fig2_idx].note.prefer_idx - 1
                #print (note1_idx)
                #print (note2_idx)

                # Swap in notebook
                tmp_note = self.notebook.notes[note1_idx]
                self.notebook.notes[note1_idx] = self.notebook.notes[note2_idx]
                self.notebook.notes[note2_idx] = tmp_note
                self.notebook.notes[note1_idx].set_dirty ()
                self.notebook.notes[note2_idx].set_dirty ()
                self.notebook.notes[note1_idx].prefer_idx = note1_idx + 1
                self.notebook.notes[note2_idx].prefer_idx = note2_idx + 1

                # Swpa in cardbox
                tmp_note = self.cards_oi [fig1_idx]
                self.cards_oi [fig1_idx] = self.cards_oi [fig2_idx]
                self.cards_oi [fig2_idx] = tmp_note

                # Refresh
                if not always_refresh:
                    self.rearrange_box ()

        # Refresh
        if always_refresh:
            self.rearrange_box ()

    def find_notes_from_fig (self, fig):
        notes = []
        for note in self.cards_oi:
            if note.fig [1] in fig:
                notes.append (note)
        return notes

    def delete_note (self, notes):
        for note in notes:
            self.cards_oi.remove (note)
            note.note.set_dirty (delete = True)
        self.notebook.Sync ()
        self.refresh_box ()
        print ("Deleted note.")

    def change_note_color (self, notes, color):
        for note in notes:
            if color != note.note.color:
                note.note.color = color
                note.note.set_dirty ()
                (x, y), (x_w, y_h) = self.graph.get_bounding_box (note.fig[0])
                self.graph.delete_figure(note.fig[0])
                bg  = self.graph.draw_rectangle (top_left = (x, y),
                                                 bottom_right = (x_w, y_h),
                                                 line_color = 'black', line_width = 1,
                                                 fill_color = note.note.color)
                self.graph.send_figure_to_back (bg)
                note.set_fig ((bg, note.fig[1]))

    def change_note_tags (self, notes, tags):
        for note in notes:
            new_note = copy(note.note)
            new_note.tags = tags
            self.notebook.update_note (note.note, new_note, True)
        print ("Updated tags.")

    def change_note_labels (self, notes, labels):
        for note in notes:
            new_note = copy(note.note)
            new_note.labels = labels
            self.notebook.update_note (note.note, new_note, True)
        print ("Updated labels.")

    def update_note (self, notes, color = None, tags = None, labels = None, delete = False):
        if delete:
            self.delete_note (notes)
            return
        if color is not None:
            self.change_note_color (notes, color)
        if tags is not None:
            self.change_note_tags (notes, tags)
            self.sync_cards  (dirty_only = True)
            self.refresh_box ()
        if labels is not None:
            self.change_note_labels (notes, labels)
            self.sync_cards  (dirty_only = True)
            self.refresh_box ()

    def init (self, window, cfg, container_scroll_cb = None):
        config = {'color': (0,0,0,255), 'margin_bottom': 8,
                  'bold_font_path' : cfg['Fonts']['Bold'],
                  'code_font_path' : cfg['Fonts']['Code'],
                  'code_font_size' : int(cfg['Fonts']['Code_size']),
                  'default_font_path': cfg['Fonts']['Dflt'],
                  'italics_font_path': cfg['Fonts']['Italic'],
                  'font_size': int(cfg['Fonts']['Size'])}

        self.md = Markdown_Ext ([(0, 0, 240)], config)
        self.window = window
        self.graph = self.window[(self.name, "graph")]
        self.container_scroll_cb = container_scroll_cb
        self.graph.widget.bind ('<MouseWheel>', self.scroll_handle)

if __name__ == '__main__':
    pass
