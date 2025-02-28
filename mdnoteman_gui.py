#!/usr/bin/env python

import sys
if sys.hexversion < 0x03070000:
    print("!!! This component requires Python version 3.7 at least !!!")
    sys.exit(1)

import FreeSimpleGUI as sg
from fsg_calendar import Calendar
from tkhtmlview import html_parser
import markdown as md
from mdnoteman_pkm import Note, Notebook
from dataclasses import dataclass, field
from typing import List, Dict
import random

default_theme = 'SystemDefault1'
window        = None
html_parser   = html_parser.HTMLTextParser()
cal           = Calendar (key_prefix = "Cal")

@dataclass
class NoteCard:
    note: Note = None
    name: str = None

    def set_html (self, html, strip = True):
        prev_state = self.widget.cget('state')
        self.widget.config (state=sg.tk.NORMAL)
        self.widget.delete ('1.0', sg.tk.END)
        self.widget.tag_delete (self.widget.tag_names)
        html_parser.w_set_html (self.widget, html, strip = strip)
        self.widget.config (state=prev_state)

    @property
    def layout (self):
        _layout = sg.Multiline(key = ("card", "content", self.name), pad = 2, size = (23, None), background_color = self.note.color, no_scrollbar = True, disabled = True)
        return _layout

    def set_content (self):
        self.set_html (md.markdown (self.note.simple_content))
        #self.window [('card', 'content', self.name)].set_size ((23, min(23, len (self.note.simple_content.splitlines()))))
        self.window [('card', 'content', self.name)].set_size ((23, random.randrange (10, 23, 3)))

    def init (self, window):
        self.window = window
        self.widget = self.window[("card", "content", self.name)].widget
        self.set_content ()

    def update (self, txt):
        pass

@dataclass
class Cardshow:
    cards : List[NoteCard] = None
    n_cols: int = 3

    @property
    def layout (self):
        _layout = []
        for c in range (self.n_cols):
            __layout = []
            for n in range (c, len (self.cards), self.n_cols):
                __layout += [[self.cards[n].layout]]
            #__layout += [[sg.VPush()]]
            _layout += [sg.Column (layout = __layout, pad = 0, vertical_alignment = 'top')]

        return [_layout]

    def init (self, window):
        for card in self.cards:
            card.init (window)

    def set_cards (self, cards = None):
        if not cards:
            self.cards = []
            for i in range (10):
                self.cards += [NoteCard(note = Note(), name = f'{i}')]
                s = random.randrange (2, 12, 2)
                self.cards [-1].note.content = "Test note " * s
        else:
            self.cards = cards


def make_label_tree (label_tree = None):
    sg_lbl_tree = sg.TreeData ()

    def parse_nested_label (label_tree, parent_key = ""):
        #for lbl in sorted(label_tree, key = lambda x: x['txt']):
        for lbl in label_tree:
            sg_lbl_tree.Insert (parent = parent_key, key = f"{parent_key}-lbl-{lbl['txt']}", text = f"{lbl['txt']} ({lbl['count']})", values = [])
            if lbl['children']:
                parse_nested_label (label_tree = lbl['children'], parent_key = f"{parent_key}-lbl-{lbl['txt']}")

    if label_tree:
        parse_nested_label (label_tree)
    else:
        sg_lbl_tree.Insert ("", "-None-", "", "")

    return sg_lbl_tree

cardshow = Cardshow ()
cardshow.set_cards ()

def make_main_window (cal, label_tree = None, tags = None, notes = None):
    menu_def = [['&Notebook', ['&Open', '---', 'E&xit']],
                ['&Edit', ['Copy (&C)', 'Cut (&X)', 'Paste (&V)', '&Undo', '&Redo']],
                ['T&ool', ['Settings']],
                ['&Help', ['&About...']]]

    mene_elem  = sg.Menu (menu_def)
    layout_mid = [[sg.Column (layout = cardshow.layout, pad = 0, scrollable = True)]]

    layout_nested_labels = [[sg.Tree(data = make_label_tree (label_tree),
                                     auto_size_columns = True,
                                     select_mode = sg.TABLE_SELECT_MODE_EXTENDED,
                                     num_rows = 20,
                                     key = '-NESTED_LBL-',
                                     show_expanded = False,
                                     enable_events = True,
                                     expand_x = True,
                                     expand_y = True,
                                     )]]

    cal_layout = cal.make_cal_layout ()

    layout_tags = [[sg.Listbox (["all"], expand_x = True, expand_y = True, key = '-TAGS-')]]

    middle_frame = sg.Frame ("Notes", key = '-MIDDLE_FRAME-', layout = layout_mid, expand_x = True, expand_y = True)

    main_pane = sg.Pane([sg.Column([[sg.Frame ("Labels", layout_nested_labels, expand_x = True, expand_y = True)],
                                    [sg.Frame ("", cal_layout)]], element_justification = 'c'),
                         sg.Column([[middle_frame]]),
                         sg.Column([[sg.Frame ("Tags", layout_tags, expand_x = True, expand_y = True, size = (50, None))]])],
                        orientation = 'horizontal', expand_x = True, expand_y = True)

    main_layout =  [[sg.Menu (menu_def)]]
    main_layout += [[sg.Button ('New Note'), sg.Input (key = '-SEARCH-', expand_x = True), sg.Button ('Graph View'), sg.Button ('Refresh')]]
    main_layout += [[main_pane]]

    return sg.Window('MD Note Manager', main_layout, finalize = True, use_default_focus = True, grab_anywhere_using_control = True, resizable = True)

def create_gui (theme = default_theme, label_tree = None):
    global cal

    sg.theme(theme)
    font = ("default", 15, 'normal')
    sg.set_options(font=font)
    window = make_main_window (cal, label_tree = label_tree)
    window.bind ("<ButtonPress-1>", ' Press')
    window.bind ("<ButtonRelease-1>", ' Release')
    #window['-NESTED_LBL-'].bind ("<ButtonPress-1>", ' Press')
    #window['-NESTED_LBL-'].bind ("<ButtonRelease-1>", ' Release')
    #window['-TAGS-'].bind ("<ButtonPress-1>", ' Press')
    #window['-TAGS-'].bind ("<ButtonRelease-1>", ' Release')
    #window['-TAGS-'].bind ("<B1-Motion>", ' Drag')
    cal.init_cal (window)
    cardshow.init (window)

    return window

def make_theme_window (theme):
    sg.theme (theme)

    layout = [[sg.Text('Theme Browser')],
              [sg.Listbox(values=sg.theme_list(), size=(20, 12), key='-LIST-', enable_events = True, select_mode = "LISTBOX_SELECT_MODE_SINGLE")],
              [sg.Button('OK'), sg.Button('Exit')]]

    return sg.Window('Theme Browser', layout, modal = True, finalize = True)

def handle (setting_cb, open_cb):
    event, values = window.read(10)

    if event not in (None, sg.TIMEOUT_KEY,):
        print (event)
        print (values)

    if event == 'Settings':
        setting_cb ()
        return True

    if event == 'Open':
        open_cb ()
        return True

    if event in (None, sg.WINDOW_CLOSED, 'Exit'):
        return False

    # Call sub-components's handles
    cal.handle (event, values)
    return True
