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
import mdnoteman_extended_sg as ext_sg
from dataclasses import dataclass, field
from typing import List, Dict

default_theme = 'SystemDefault1'
window        = None
cal           = Calendar (key_prefix = "Cal")

@dataclass
class NoteCard:
    note: Note = None
    name: str = None
    window: ext_sg.Window = None
    parser: html_parser.HTMLTextParser = html_parser.HTMLTextParser ()

    def fit_height (self):
        widget = self.window[("card", self.name, 'ctn')].widget
        widget.update ()
        need_lines = widget.count ("1.0", "end", "displaylines") [0] - 2
        self.window[("card", self.name, 'ctn')].set_size ((None, 20 if need_lines > 20 else need_lines))

    def set_html (self, html, strip = True):
        widget = self.window[("card", self.name, 'ctn')].widget
        prev_state = widget.cget('state')
        widget.config (state=sg.tk.NORMAL)
        widget.delete ('1.0', sg.tk.END)
        widget.tag_delete (widget.tag_names)
        self.parser.w_set_html (widget, html, strip = strip)
        widget.config (state=prev_state)

    @property
    def layout (self):
        _e = sg.Column ([[sg.Multiline(key = ("card", self.name, 'ctn'), pad = ((8,8), (8,1)), border_width = 1,
                                       size = (23, 3), background_color = self.note.color,
                                       no_scrollbar = True, disabled = True, write_only = True,
                                       expand_x = True, expand_y = True)],
                         [sg.Text(key = ('card', self.name, 'ctx'), pad = ((8,8),(1,8)), border_width = 1,
                                  size = (23,3), background_color = self.note.color,
                                  expand_x = True, expand_y = True)]], key = ("card", self.name))
        return _e

    def set_content (self):
        self.set_html (md.markdown (self.note.simple_content))
        self.fit_height ()
        self.window[("card", self.name, 'ctx')].print (self.note.simple_context)


    def scroll_handle (self, event):
        if self.container_scroll_cb:
            self.container_scroll_cb (event)
        return 'break'

    def init (self, window, container_scroll_cb = None):
        self.window = window
        self.window [('card', self.name)].set_cursor (cursor = 'left_ptr')
        self.container_scroll_cb = container_scroll_cb
        self.window[("card", self.name, 'ctn')].widget.configure (relief = 'groove')
        self.window[("card", self.name, 'ctn')].widget.bind ('<MouseWheel>', self.scroll_handle)
        self.window[("card", self.name, 'ctx')].widget.configure (relief = 'groove')
        self.window[("card", self.name, 'ctx')].widget.bind ('<MouseWheel>', self.scroll_handle)

        self.set_content ()

    def update (self, txt):
        pass

@dataclass
class CardBox:
    cards : List[NoteCard] = field (default_factory = lambda: [])
    n_cols: int = 3
    window: ext_sg.Window = None
    name  : str = ''
    width : int = 768

    @property
    def layout (self):
        _layout = []
        return [_layout]

    def add_cards (self, notes):
        for note in notes:
            self.cards.insert (0, NoteCard(note = note, name = note.name) )

        if self.window:
            self.refresh_box ()

    def arrange_cards (self, old_n_cols):
        self.cards[0].widget.destroy ()
        self.cards[0].widget.master.destroy ()
        self.cards[0].widget.master.master.destroy ()
        self.window [(self.name + 'col', 0)].widget.update ()

    def resize (self, width):
        self.width = width
        old_n_cols = self.n_cols
        self.n_cols = self.width // 256

        if self.n_cols > old_n_col:
            for i in range (old_n_cols, self.n_cols):
                self.window.extend_layout (self.window [self.name], [[sg.Column (key = (self.name + 'col', i),
                                                                                 layout = [], pad = 0, vertical_alignment = 'top')]])
        elif self.n_cols < old_n_cols:
            for i in range (self.n_cols, old_n_cols):
                self.window[(self.name + 'col', i)].widget.destroy ()

        if self.n_cols != old_n_cols:
            self.arrange_cards (old_n_cols)
            self.window [self.name].widget.update ()
            self.window [self.name].contents_changed ()
            self.window [self.name].expand (expand_row = True)

    def refresh_box (self):
        self.n_cols = self.width // 256
        _layout = list ()
        N = len (self.cards)

        for c in range (self.n_cols):
            __layout = list ()
            for n in range (c, N, self.n_cols):
                __layout.append ([self.cards[n].layout])
            _layout.append (sg.Column (key = (self.name + 'col', c),
                                       layout = __layout, pad = 0, vertical_alignment = 'top'))

        self.window.new_layout (self.window [self.name], [_layout])

        for n in range (N):
            self.cards [n].init (self.window, self.window[self.name].TKColFrame.yscroll)

        self.window [self.name].widget.update ()
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

    win = ext_sg.Window('MD Note Manager', main_layout, finalize = True, use_default_focus = True, grab_anywhere_using_control = True, resizable = True)
    rwidth = win['-RIGHT_PANE-'].get_size()[0]
    lwidth = win['-LEFT_PANE-'].get_size()[0]
    win['-PANE-'].widget.paneconfig (win['-MIDDLE_PANE-'].widget, minsize = 272)
    win['-PANE-'].widget.paneconfig (win['-RIGHT_PANE-'].widget, minsize = rwidth)
    win['-PANE-'].widget.paneconfig (win['-LEFT_PANE-'].widget, minsize = lwidth)
    win.set_min_size ((lwidth + rwidth + 280, 200))

    win.bind ("<ButtonPress-1>", ' Press')
    win.bind ("<ButtonRelease-1>", ' Release')
    win.bind ("<Configure>", ' Resize')
    #win['-PANE-'].bind ("<B1-Motion>", ' Drag')
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

    return ext_sg.Window('Theme Browser', layout, modal = True, finalize = True)

def theme_change (cfg):
    old_theme = sg.theme ()
    new_theme = old_theme
    selected  = old_theme

    setting_window = make_theme_window (selected)
    list_of_themes = setting_window['-LIST-'].get_list_values ()
    selected_idx   = list_of_themes.index (selected)
    setting_window['-LIST-'].update (scroll_to_index = selected_idx, set_to_index = selected_idx)

    while True:  # Event Loop
        event, values  = setting_window.read()
        if event == '-LIST-':
            selected_theme = values['-LIST-'][0]
            selected_idx   = setting_window['-LIST-'].get_indexes ()[0]
            if selected_theme != selected:
                setting_window.close ()
                selected = selected_theme
                setting_window = make_theme_window (selected_theme)
                setting_window['-LIST-'].update (scroll_to_index = selected_idx, set_to_index = selected_idx)
            continue

        if event in (sg.WIN_CLOSED, 'Exit'):
            sg.theme (old_theme)
            break
        if event == 'OK':
            new_theme = selected_theme
            break

    setting_window.close ()
    if new_theme != old_theme:
        window.close ()
        window = create_gui (new_theme)
        cfg['Appearance']['Theme'] = new_theme

    return cfg

def handle (setting_cb, open_cb):
    event, values = window.read(10)

    #if event not in (None, sg.TIMEOUT_KEY, '__TIMER EVENT__'):
    #    print (event)
    #    print (values)

    if event in ('__TIMER EVENT__', ' Resize'):
        # If cardbox was changed size, trigger refresh cardbox view
        cardbox_width = window[cardbox.name].get_size ()[0]
        if abs (cardbox_width - cardbox.width) > 230:
            window.write_event_value (cardbox.name, cardbox_width)

    if event == 'Settings':
        setting_cb ()
        return True

    if event == 'Open':
        open_cb ()
        return True

    if event == cardbox.name:
        cardbox.resize (values ['cardbox'])
        return True

    if event in (None, sg.WINDOW_CLOSED, 'Exit'):
        return False

    # Call sub-components's handles
    cal.handle (event, values)
    return True
