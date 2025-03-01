#!/usr/bin/env python

import sys
if sys.hexversion < 0x03070000:
    print("!!! This component requires Python version 3.7 at least !!!")
    sys.exit(1)

import FreeSimpleGUI as sg
from fsg_calendar import Calendar
from tkhtmlview import html_parser
import tkinter as tk
import markdown as md
from mdnoteman_pkm import Note, Notebook
from dataclasses import dataclass, field
from typing import List, Dict

default_theme = 'SystemDefault1'
window        = None
html_parser   = html_parser.HTMLTextParser()
cal           = Calendar (key_prefix = "Cal")

def set_size(element, size):
    # Only work for sg.Column when `scrollable=True` or `size not (None, None)`
    options = {'width':size[0], 'height':size[1]}
    if element.Scrollable or element.Size != (None, None):
        element.widget.canvas.config(**options)
    else:
        element.widget.pack_propagate(0)
        element.set_size(size)

@dataclass
class NoteCard:
    note: Note = None
    name: str = None
    window: sg.Window = None
    widget: tk.Text = None

    def fit_height (self):
        h = 0
        while h < 20:
            h += 1
            self.widget.config (height = h + 0.5)
            self.widget.master.update ()
            if self.widget.yview()[1] >= 1:
                break

    def set_html (self, html, strip = False):
        prev_state = self.widget.cget('state')
        self.widget.config (state=sg.tk.NORMAL)
        self.widget.delete ('1.0', sg.tk.END)
        self.widget.tag_delete (self.widget.tag_names)
        html_parser.w_set_html (self.widget, html, strip = strip)
        self.widget.config (state=prev_state)

    @property
    def element (self):
        _layout = sg.Multiline(key = ("card", "content", self.name), pad = 8, border_width = 1,
                               size = (23, 3), background_color = self.note.color,
                               no_scrollbar = True, disabled = True, write_only = True,
                               expand_x = True, expand_y = True)
        return _layout

    def set_content (self):
        self.set_html (md.markdown (self.note.simple_content))
        self.fit_height ()

    def init (self, window):
        self.window = window
        self.window [('card', 'content', self.name)].set_cursor (cursor = 'left_ptr')
        self.widget = self.window[("card", "content", self.name)].widget
        self.widget.configure (relief = 'groove')

        self.set_content ()

    def update (self, txt):
        pass

@dataclass
class CardBox:
    cards : List[NoteCard] = field (default_factory = lambda: [])
    n_cols: int = 3
    window: sg.Window = None
    name  : str = ''
    width : int = 768

    @property
    def layout (self):
        _layout = []
        return [_layout]

    def add_cards (self, notes):
        for note in notes:
            self.cards = [NoteCard(note = note, name = note.name)] + self.cards

        if self.window:
            self.refresh_box ()

    def resize (self, width):
        self.width = width
        old_n_cols = self.n_cols
        self.n_cols = self.width // 256
        if self.n_cols > old_n_cols:
            pass
        elif self.n_cols < old_n_cols:
            pass

    def refresh_box (self):
        self.n_cols = self.width // 256

        self.window.extend_layout (self.window [self.name], [[sg.Column (key = (self.name + 'col', i),
                                                                         layout = [], pad = 0, vertical_alignment = 'top') for i in range (self.n_cols)]])
        for c in range (self.n_cols):
            for n in range (c, len (self.cards), self.n_cols):
                self.window.extend_layout (self.window [(self.name + 'col', c)], [[self.cards[n].element]])
                self.cards [n].init (window)
        self.window [self.name].contents_changed ()
        self.window [self.name].expand (expand_row = True)

    def init (self, window):
        self.window = window

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

cardbox = CardBox (name = 'cardbox')

def make_main_window (cal, label_tree = None, tags = None, notes = None):
    menu_def = [['&Notebook', ['&Open', '---', 'E&xit']],
                ['&Edit', ['Copy (&C)', 'Cut (&X)', 'Paste (&V)', '&Undo', '&Redo']],
                ['T&ool', ['Settings']],
                ['&Help', ['&About...']]]

    mene_elem  = sg.Menu (menu_def)
    layout_mid = [[sg.Column (key = cardbox.name, layout = cardbox.layout, pad = 0,
                              scrollable = True, vertical_scroll_only = True,
                              expand_x = True, expand_y = True, size = (cardbox.width, None))]]

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
                                    [sg.Frame ("", cal_layout)]], element_justification = 'c', key = '-LEFT_PANE-'),
                         sg.Column([[middle_frame]], key = '-MIDDLE_PANE-'),
                         sg.Column([[sg.Frame ("Tags", layout_tags, expand_x = True, expand_y = True, size = (150, None))]], key = '-RIGHT_PANE-')],
                        orientation = 'horizontal', expand_x = True, expand_y = True, key = '-PANE-', relief = 'groove', show_handle = False)

    main_layout =  [[sg.Menu (menu_def)]]
    main_layout += [[sg.Button ('New Note'), sg.Input (key = '-SEARCH-', expand_x = True), sg.Button ('Graph View'), sg.Button ('Refresh')]]
    main_layout += [[main_pane]]

    win = sg.Window('MD Note Manager', main_layout, finalize = True, use_default_focus = True, grab_anywhere_using_control = True, resizable = True)
    win['-PANE-'].widget.paneconfig (win['-MIDDLE_PANE-'].widget, minsize = 272)
    win['-PANE-'].widget.paneconfig (win['-RIGHT_PANE-'].widget, minsize = 170)
    win['-PANE-'].widget.paneconfig (win['-LEFT_PANE-'].widget, minsize = 240)

    win.bind ("<ButtonPress-1>", ' Press')
    win.bind ("<ButtonRelease-1>", ' Release')
    win['-PANE-'].bind ("<B1-Motion>", ' Drag')
    #win['-NESTED_LBL-'].bind ("<ButtonPress-1>", ' Press')
    #win['-NESTED_LBL-'].bind ("<ButtonRelease-1>", ' Release')
    #win['-TAGS-'].bind ("<ButtonPress-1>", ' Press')
    #win['-TAGS-'].bind ("<ButtonRelease-1>", ' Release')
    #win['-TAGS-'].bind ("<B1-Motion>", ' Drag')
    return win

def create_gui (theme = default_theme, label_tree = None):
    global cal
    global cardbox

    sg.theme(theme)
    font = ("default", 15, 'normal')
    sg.set_options(font=font)
    window = make_main_window (cal, label_tree = label_tree)
    cal.init_cal (window)
    cardbox.init (window)

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

    if event == '-PANE- Drag':
        cardbox_size = window[cardbox.name].get_size ()
        if abs (cardbox_size [0] - cardbox.width) > 256:
            #window.write_event_value (cardbox.name, cardbox_size [0])
            cardbox.resize (cardbox_size [0])
    if event in (None, sg.WINDOW_CLOSED, 'Exit'):
        return False

    # Call sub-components's handles
    cal.handle (event, values)
    return True
