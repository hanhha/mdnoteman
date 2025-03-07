#!/usr/bin/env python

import sys
if sys.hexversion < 0x03070000:
    print("!!! This component requires Python version 3.7 at least !!!")
    sys.exit(1)

import FreeSimpleGUI as sg
from fsg_calendar import Calendar
from tkhtmlview import html_parser
import tkinter as tk
from md2img import Markdown_Ext
from mdnoteman_pkm import Note, Notebook
from dataclasses import dataclass, field
from typing import List, Dict
from PIL import Image, ImageDraw, ImageFont
import io
import base64

default_theme = 'SystemDefault1'
window        = None
cal           = Calendar (key_prefix = "Cal")

@dataclass
class NoteCard:
    note: Note = None
    name: str = None
    width: int = 240
    _thumbnail: Image = None
    _thumbnail_bio: io.BytesIO = None
    md : Markdown_Ext = None

    @property
    def thumbnail (self):
        return self._thumbnail

    @property
    def thumbnail_bio (self):
        return self._thumbnail_bio

    def set_fig (self, fig):
        self.fig = fig

    def init (self):
        self.md = Markdown_Ext ([(0, 0, self.width)], {'color': (0,0,0,255), 'margin_bottom': 8})
        self.update ()

    def update (self):
        ctn = self.md.convert_img (self.note.simple_content)
        ctx = self.md.convert_img (self.note.simple_context)
        ctn_h = 240 if (ctn.size[1] > 240) else ctn.size[1]
        img = Image.new ("RGBA", (self.width, ctn_h + ctx.size [1]))
        img.paste (ctn, (0, 0))
        img.paste (ctx, (0, ctn_h))
        bio = io.BytesIO ()
        img.save (bio, format = "PNG")
        self._thumbnail = img.copy ()
        self._thumbnail_bio = bio.getvalue ()
        del img

@dataclass
class CardBox:
    cards : List[NoteCard] = field (default_factory = lambda: [])
    n_cols: int = 3
    window: sg.Window = None
    name  : str = ''
    width : int = 768
    tags_oi: List[str] = field (default_factory = lambda: [])
    labels_oi: List[str] = field (default_factory = lambda: [])
    tags_oni: List[str] = field (default_factory = lambda: [])
    labels_oni: List[str] = field (default_factory = lambda: [])

    def scroll_handle (self, event):
        if self.container_scroll_cb:
            self.container_scroll_cb (event)
        return 'break'

    @property
    def layout (self):
        _layout = [(sg.Graph (key = (self.name, "graph"),
                              canvas_size = (self.width, 1), graph_bottom_left = (0, 1), graph_top_right = (self.width, 0),
                              expand_x = True, expand_y = True, enable_events = True, drag_submits = True))]
        return [_layout]

    @property
    def cards_oi (self):
        """ return cards of interest """
        return self._cards_oi

    def filter_cards (self, tags = None, labels = None, excl_tags = None, excl_labels = None):
        self.tags_oi    = tags or self.tags_oi
        self.labels_oi  = labels or self.labels_oi
        self.tags_oni   = excl_tags or self.tags_oni
        self.labels_oni = excl_labels or self.labels_oni

        self._cards_oi = []
        for card in self.cards:
            selected = False
            l = len(self.labels_oi)
            for lbl in card.note.labels:
                if ((l == 0) or (lbl in self.labels_oi)) and (lbl not in self.labels_oni):
                    selected = True
                    break
            if selected:
                selected = False
                l = len(self.tags_oi)
                for tag in card.note.tags:
                    if ((l == 0) or (tag in self.tags_oi)) and (tag not in self.tags_oni):
                        selected = True
                        break

            if selected:
                self._cards_oi.append (card)


    def add_cards (self, notes):
        for note in notes:
            card = NoteCard(note = note, name = note.name)
            card.init ()
            self.cards.insert (0, card)

        self.filter_cards ()

        if self.window:
            self.refresh_box ()

    def erase (self):
        self.window[(self.name, "graph")].set_size ((self.width, 1))
        self.window[(self.name, "graph")].change_coordinates ((0, 1), (self.width, 0))
        self.window[(self.name, "graph")].erase()

    def resize (self, width):
        self.width = width
        old_n_cols = self.n_cols
        self.n_cols = self.width // 256

        if self.n_cols != old_n_cols:
            self.erase ()
            self.refresh_box ()

    def refresh_box (self):
        self.n_cols = self.width // 256
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
            if y + 16 + h > self.window[(self.name, "graph")].CanvasSize [1]:
                self.window[(self.name, "graph")].set_size ((self.width, y + 16 + h))
                self.window[(self.name, "graph")].change_coordinates ((0, y + 16 + h), (self.width, 0))

            bg  = self.window[(self.name, "graph")].draw_rectangle (top_left = (c * 256 + 6, y + 6), bottom_right = (c * 256 + 8 + w + 2, y + 8 + h + 2), line_color = 'black', line_width = 1, fill_color = 'white')
            fig = self.window[(self.name, "graph")].draw_image (data = self.cards_oi[n].thumbnail_bio, location = (c * 256 + 8, y + 8))
            self.cards_oi[n].set_fig ((bg, fig))
            c = 0 if (c + 1 == self.n_cols) else c + 1

        self.window [self.name].widget.update ()
        self.window [self.name].contents_changed ()
        self.window [self.name].expand (expand_row = True)

    def init (self, window, container_scroll_cb = None):
        self.window = window
        self.container_scroll_cb = container_scroll_cb
        self.window[(self.name, 'graph')].widget.bind ('<MouseWheel>', self.scroll_handle)

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
                              vertical_alignment = 'top',
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

    with open ("assets/head.png", "rb") as ico:
        s = base64.b64encode(ico.read())
    win = sg.Window('MD Note Manager', main_layout, finalize = True, use_default_focus = True, grab_anywhere_using_control = True, resizable = True, use_ttk_buttons = True, ttk_theme = sg.DEFAULT_TTK_THEME, icon = s)
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
    cardbox.init (window, window[cardbox.name].TKColFrame.yscroll)

    return window

def make_theme_window (theme):
    sg.theme (theme)

    layout = [[sg.Text('Theme Browser')],
              [sg.Listbox(values=sg.theme_list(), size=(20, 12), key='-LIST-', enable_events = True, select_mode = "LISTBOX_SELECT_MODE_SINGLE")],
              [sg.Button('OK'), sg.Button('Exit')]]

    return sg.Window('Theme Browser', layout, modal = True, finalize = True)

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
