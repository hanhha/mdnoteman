#!/usr/bin/env python

import sys
if sys.hexversion < 0x03070000:
    print("!!! This component requires Python version 3.7 at least !!!")
    sys.exit(1)

import FreeSimpleGUI as sg
from fsg_calendar import Calendar
import fsg_extend as esg
from tkhtmlview import html_parser
import tkinter as tk
from md2img import Markdown_Ext
from mdnoteman_pkm import Note, Notebook
from dataclasses import dataclass, field
from typing import List, Dict, Set
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import re
import mdnoteman_dsl as dsl

debug = False
default_theme = 'SystemDefault1'
window        = None
window_stack  = []
cal           = Calendar (key_prefix = "Cal")

assets = {}

with open ("assets/head.png", "rb") as ico:
    assets['win_ico'] = base64.b64encode(ico.read())
with open ("assets/refresh.png", "rb") as ico:
    assets['refresh_ico'] = base64.b64encode(ico.read())
with open ("assets/notes.png", "rb") as ico:
    assets['note_ico'] = base64.b64encode(ico.read())
with open ("assets/knowledge-graph.png", "rb") as ico:
    assets['graph_ico'] = base64.b64encode(ico.read())
with open ("assets/trash-bin.png", "rb") as ico:
    assets['trashbin_ico'] = base64.b64encode(ico.read())
with open ("assets/building-plan.png", "rb") as ico:
    assets['drawing_ico'] = base64.b64encode(ico.read())
with open ("assets/color.png", "rb") as ico:
    assets['color_ico'] = base64.b64encode(ico.read())
with open ("assets/picture.png", "rb") as ico:
    assets['picture_ico'] = base64.b64encode(ico.read())

def push_nested_window (_win, modal = False):
    global window_stack

    window_stack.append ((_win, modal))
    if modal:
        window_stack[-1][0].TKroot.grab_set()

def pop_nested_window (_win = None):
    global window_stack
    
    en = False

    if _win is not None:
        if _win == window_stack [-1][0]:
            en = True
    else:
        en = True

    if en:
        win = window_stack.pop ()
        if len(window_stack) > 0:
            if window_stack[-1][1]:
                window_stack[-1][0].TKroot.grab_set()

        win[0].close ()

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

    def sync_cards (self):
        print ("Syncing cards to box ...")

        for note in self.notebook.notes:
            card = NoteCard(note = note)
            card.init (self.md)
            self.add_or_replace (card)

        self.filter ()

        print ("Done.")

    def add_or_replace (self, card):
        for i in range(len(self.cards)):
            if self.cards[i].note.timestamp == card.note.timestamp:
                ret = self.cards[i]
                self.cards[i] = card
                return ret
        self.cards.insert (0, card)
        return None

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
        if color is not None:
            for note in notes:
                if color != note.note.color:
                    note.note.color = '#' + color
                    note.note.set_dirty ()
                    (x, y), (x_w, y_h) = self.graph.get_bounding_box (note.fig[0])
                    self.graph.delete_figure(note.fig[0])
                    bg  = self.graph.draw_rectangle (top_left = (x, y),
                                                     bottom_right = (x_w, y_h),
                                                     line_color = 'black', line_width = 1,
                                                     fill_color = note.note.color)
                    self.graph.send_figure_to_back (bg)
                    note.set_fig ((bg, note.fig[1]))

    def init (self, window, container_scroll_cb = None):
        self.md = Markdown_Ext ([(0, 0, 240)], {'color': (0,0,0,255), 'margin_bottom': 8})
        self.window = window
        self.graph = self.window[(self.name, "graph")]
        self.container_scroll_cb = container_scroll_cb
        self.graph.widget.bind ('<MouseWheel>', self.scroll_handle)

def make_label_tree (label_tree = None):
    sg_lbl_tree = sg.TreeData ()

    def parse_nested_label (label_tree, parent_key = ""):
        #for lbl in sorted(label_tree, key = lambda x: x['txt']):
        for lbl in sorted (label_tree.keys()):
            sg_lbl_tree.Insert (parent = parent_key, key = f"{parent_key}-lbl-{lbl}", text = f"{lbl} ({label_tree[lbl]['count']})", values = [])
            if label_tree[lbl]['children']:
                parse_nested_label (label_tree = label_tree[lbl]['children'], parent_key = f"{parent_key}-lbl-{lbl}")

    if label_tree:
        parse_nested_label (label_tree)
    else:
        sg_lbl_tree.Insert ("", "-None-", "", "")

    return sg_lbl_tree

cardbox = CardBox (name = 'cardbox')

def make_main_window (cal, label_tree = None, tags = None, notes = None):
    global assets, debug

    menu_def = [['&Notebook', ['&Open::menu', '---', 'E&xit::menu']],
                ['&Edit', ['Copy (&C)::menu', 'Cut (&X)::menu', 'Paste (&V)::menu', '&Undo::menu', '&Redo::menu']],
                ['T&ool', ['Settings::menu']],
                ['&Help', ['&About...::menu']]]

    mene_elem  = sg.Menu (menu_def)
    layout_mid = [[sg.Column (key = cardbox.name, layout = cardbox.layout, pad = 0,
                              scrollable = True, vertical_scroll_only = True,
                              vertical_alignment = 'top',
                              expand_x = True, expand_y = True, size = (cardbox.width, None))]]

    layout_nested_labels = [[sg.Tree(data = sg.TreeData(),
                                     auto_size_columns = True,
                                     select_mode = sg.TABLE_SELECT_MODE_EXTENDED,
                                     click_toggles_select = True,
                                     num_rows = 20,
                                     key = '-NESTED_LBL-',
                                     show_expanded = False,
                                     enable_events = True,
                                     expand_x = True,
                                     expand_y = True,
                                     )]]

    cal_layout = cal.make_cal_layout ()

    layout_tags = [[sg.Listbox (["all"], expand_x = True, expand_y = True,
                                key = '-TAGS-',
                                enable_events = True,
                                select_mode = sg.TABLE_SELECT_MODE_EXTENDED)]]

    middle_frame = sg.Frame ("Notes", key = '-MIDDLE_FRAME-', layout = layout_mid, expand_x = True, expand_y = True)

    main_pane = sg.Pane([sg.Column([[sg.Frame ("Labels", layout_nested_labels, expand_x = True, expand_y = True)],
                                    [sg.Frame ("", cal_layout)]], element_justification = 'c', key = '-LEFT_PANE-'),
                         sg.Column([[middle_frame]], key = '-MIDDLE_PANE-'),
                         sg.Column([[sg.Frame ("Tags", layout_tags, expand_x = True, expand_y = True, size = (150, None))]], key = '-RIGHT_PANE-')],
                        orientation = 'horizontal', expand_x = True, expand_y = True, key = '-PANE-', relief = 'groove', show_handle = False)

    main_layout =  [[sg.Menu (menu_def)]]
    main_layout += [[sg.Button ('', image_source = assets['note_ico'], border_width = 1, image_subsample = 15,
                                button_color = (sg.theme_background_color(), sg.theme_background_color ()),
                                key = '-BTN-NOTE-'),
                     sg.Input (key = '-SEARCH-', expand_x = True,
                               default_text = 'Search query', do_not_clear = True),
                     sg.Button ('',image_source = assets['graph_ico'], border_width = 1, image_subsample = 15,
                                button_color = (sg.theme_background_color(), sg.theme_background_color ()),
                                key = '-BTN-GRAPH-'),
                     sg.Button ('', image_source = assets['refresh_ico'], border_width = 1, image_subsample = 15,
                                button_color = (sg.theme_background_color(), sg.theme_background_color ()),
                                key = '-BTN-REFRESH-')]]
    main_layout += [[main_pane]]
    main_layout += [[sg.Frame ("Info", layout = [[sg.Multiline (key = '-INFO-', expand_x = True, disabled = True,
                                                                size = (None, 5), write_only = True,
                                                                reroute_stdout = not debug, autoscroll = True)]],
                               expand_x = True)]]

    win = sg.Window('MD Note Manager', main_layout, finalize = True,
                    use_default_focus = True, grab_anywhere_using_control = True,
                    resizable = True, use_ttk_buttons = True,
                    ttk_theme = sg.DEFAULT_TTK_THEME, icon = assets['win_ico'])
    push_nested_window (win, False)

    rwidth = win['-RIGHT_PANE-'].get_size()[0]
    lwidth = win['-LEFT_PANE-'].get_size()[0]
    win['-PANE-'].widget.paneconfig (win['-MIDDLE_PANE-'].widget, minsize = 272)
    win['-PANE-'].widget.paneconfig (win['-RIGHT_PANE-'].widget, minsize = rwidth)
    win['-PANE-'].widget.paneconfig (win['-LEFT_PANE-'].widget, minsize = lwidth)
    win.set_min_size ((lwidth + rwidth + 280, 200))

    #win.bind ("<ButtonPress-1>", ' Press')
    #win.bind ("<ButtonRelease-1>", ' Release')
    win.bind ("<Configure>", ' Resize')
    win['-SEARCH-'].bind ("<Return>", "")
    win['-SEARCH-'].bind ('<FocusIn>', '+INPUT FOCUS+')
    #win['-PANE-'].bind ("<B1-Motion>", ' Drag')
    #win['-NESTED_LBL-'].bind ("<ButtonPress-1>", ' Press')
    #win['-NESTED_LBL-'].bind ("<ButtonRelease-1>", ' Release')
    #win['-TAGS-'].bind ("<ButtonPress-1>", ' Press')
    #win['-TAGS-'].bind ("<ButtonRelease-1>", ' Release')
    #win['-TAGS-'].bind ("<B1-Motion>", ' Drag')
    return win

def update_show_labels (lbl_tree):
    if lbl_tree:
        tree_data = make_label_tree (lbl_tree)

        old_vscroll = window ["-NESTED_LBL-"].widget.yview () [0]
        window ["-NESTED_LBL-"].update (values = tree_data)
        window ["-NESTED_LBL-"].set_vscroll_position (old_vscroll)

def update_show_tags (tags = None):
    if tags:
        values = ["all"]
        for k in sorted(tags.keys()):
            values.append (f"{k} ({tags[k]})")

        old_vscroll = window ["-TAGS-"].widget.yview () [0]
        window ["-TAGS-"].update (values = values)
        window ["-TAGS-"].set_vscroll_position (old_vscroll)

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

def call_tags_chooser_window (title, tags, selected_tags, relax_list_order = False, location = None, row_limit = 8):
    '''Create a floating window to select tags or labels
        relax_list_order: selected tags will be shown first, then tags with high number of notes'''

    prev_cb = []

    # Reorder list
    for k, v in tags.items():
        k_selected = k in selected_tags
        l = len(prev_cb)
        if l > 0:
            i = 0
            while (i < l):
                pk, pv = list(prev_cb[i].items())[0]
                p_selected = pk in selected_tags
                if relax_list_order:
                    if not k_selected:
                        if p_selected or (v < pv[0]):
                            i += 1
                        else:
                            break
                    if k_selected:
                        if p_selected and (v < pv[0]):
                            i += 1
                        else:
                            break
                else:
                    if k < pk: # in abc order of keys
                        i += 1
                    else:
                        break
            if i < l:
                prev_cb.insert (i, {k : (v, k_selected)})
            else:
                prev_cb.append ({k : (v, k_selected)})
        else:
            prev_cb.append ({k : (v, k_selected)})

    #print (f"len(tags) = {len(tags)} : len(prev_cb) = {len(prev_cb)}")

    # Create list of Checkbox
    sub_cb = []
    cb     = []
    i = 0
    for tag_e in prev_cb:
        tag, v = list(tag_e.items())[0]
        if relax_list_order:
            sub_cb.append ([sg.pin(sg.Checkbox(tag, key = tag, expand_x = True, default = tag in selected_tags),
                                   shrink = True)])
            if (i + 1 == row_limit):
                cb.append (sg.Column(sub_cb))
                sub_cb = []
                i = 0
            else:
                i += 1
        else:
            cb.append ([sg.Checkbox(tag, key = tag, expand_x = True, default = tag in selected_tags)])
    if relax_list_order and len(sub_cb) > 0:
        cb.append (sg.vtop(sg.Column(sub_cb)))
  
    layout = [[sg.Text (title)],
              [sg.Input (key = '-IN-', enable_events = True)],
              cb]
    _win = sg.Window ('', layout = layout, modal = True,
                      no_titlebar = True,
                      keep_on_top = True, location = (location[0], location[1] - 32),
                      finalize = True, icon = assets['win_ico'],
                      resizable = False)
    push_nested_window (_win, False)
    _win.bind ('<FocusOut>', 'LostFocus')
    _win.bind ('<Escape>', 'ESC')
    _win['-IN-'].bind('<Return>', 'Enter')
    #_win['-IN-'].bind('<Escape>', 'ESC')

    tags_inp = []
    new_tags = selected_tags
    input_txt = ''

    while True:
        event, values = _win.read ()
        #if event not in (None, sg.TIMEOUT_KEY, '__TIMER EVENT__'):
        #    print (event)
        #    print (values)

        if event == '-IN-':
            [*inp, recent_inp] = re.split(r'[,\s]+', values['-IN-'].strip())
            if values['-IN-'] == input_txt:
                continue
            else:
                input_txt = values['-IN-']
                [*inp, recent_inp] = re.split(r'[,\s]+', input_txt.strip())
                if recent_inp != '':
                    for tag in tags.keys():
                        if not tag.startswith(recent_inp):
                            _win[tag].update (visible = False)
                else:
                    for tag in tags.keys():
                        _win[tag].update (visible = True)

        if event == '-IN-Enter':
            strip_inp = values['-IN-'].strip(', ')
            tags_inp = re.split(r'[,\s]+', strip_inp) if (strip_inp != '') else []
            break

        if event == 'LostFocus':
            if _win.find_element_with_focus() is None:
                new_tags = []
                for k in tags.keys():
                    if values[k]:
                        new_tags.append (k)
                break

        if event == 'ESC':
            new_tags = []
            for k in tags.keys():
                if values[k]:
                    new_tags.append (k)
            break

    pop_nested_window (_win)

    new_tags.extend (tags_inp)
    return list(set(new_tags)) 

def call_color_chooser_window (color = None, location = None):
    color_dict = {}
    color_dict ['White']        = 'FFFFFF'
    color_dict ['Pink']         = 'FF69B4'
    color_dict ['Gray']         = 'ABABAB'
    color_dict ['Yellow']       = 'FFFF00'
    color_dict ['Light Blue']   = '87CEFA'
    color_dict ['Light Green']  = '90EE90'
    color_dict ['Light Purple'] = '9370DB'

    prev = {}
    prev ['FFFFFF'] = False
    prev ['FF69B4'] = False
    prev ['ABABAB'] = False
    prev ['FFFF00'] = False
    prev ['87CEFA'] = False
    prev ['90EE90'] = False
    prev ['9370DB'] = False

    cb = []
    for k,v in color_dict.items():
        cb.append ([sg.Checkbox(k, key = v, background_color = '#' + v, expand_x = True)])

    _win = sg.Window ('', layout = cb, modal = True,
                      no_titlebar = True,
                      keep_on_top = True, location = (location[0], location[1] - 32),
                      finalize = True, icon = assets['win_ico'],
                      resizable = False)
    push_nested_window (_win, False)
    _win.bind ('<FocusOut>', 'LostFocus')
    _win.bind ('<ButtonRelease-1>', 'Release')
    _win.bind ('<Escape>', 'ESC')

    selected = color
    if color is not None:
        _win[color].update (value = True)
        prev[color] = True

    while True:
        event, values = _win.read ()
        #if event not in (None, sg.TIMEOUT_KEY, '__TIMER EVENT__'):
        #    print (event)
        #    print (values)

        if event == 'Release':
            for v in color_dict.values():
                val = _win[v].get ()
                if val != prev [v]:
                    prev[v] = val
                    _win.write_event_value (v, val)
                    break

        if event in prev.keys():
            if values[event]:
                for k in prev.keys():
                    if k != event:
                        _win[k].update (value = False)
                selected = event
                break

        if event in ('ESC', 'LostFocus'):
            break

    pop_nested_window (_win)
    return selected

def call_edit_window (note = None):
    if note is not None:
        ctn    = note.content
        tags   = note.tags
        labels = note.labels
        links  = note.links
        color  = note.color
    else:
        ctn    = 'Take a note in MD format ...'
        tags   = []
        labels = []
        links  = []
        color  = '#FFFFFF' # White

    md_layout = [[sg.Multiline (key = '-EDT-NOTE-', expand_x = True, expand_y = True,
                                default_text = ctn,
                                do_not_clear = True)]]
    preview_layout = [[]]
    layout = [[sg.TabGroup([[sg.Tab('Markdown', md_layout, tooltip = 'Markdown format'),
                             sg.Tab('Preview', preview_layout, tooltip = 'Preview')]], expand_x = True, expand_y = True)],
              [sg.Button (key = '-BTN-COLOR-', border_width = 1, image_source = assets['color_ico'],
                          button_color = (color, color),
                          image_subsample = 15, tooltip = "Change background color of note"),
               sg.Button ('Add labels'),
               sg.Button ('Add tags'),
               sg.Button (key = '-BTN-IMG-', border_width = 1, image_source = assets['picture_ico'],
                          button_color = (sg.theme_background_color(), sg.theme_background_color ()),
                          image_subsample = 16, tooltip = 'Add image to note'),
               sg.Button (key = '-BTN-DWG-', border_width = 1, image_source = assets['drawing_ico'],
                          button_color = (sg.theme_background_color(), sg.theme_background_color ()),
                          image_subsample = 16, tooltip = 'Add drawing to note'),
               sg.Push(),
               sg.Button (key = '-BTN-DEL-', border_width = 1, image_source = assets['trashbin_ico'],
                          button_color = (sg.theme_background_color(), sg.theme_background_color ()),
                          image_subsample = 16, tooltip = 'Delete note')],
              [sg.Frame ("Assets", layout = [
                        [sg.Listbox(['nothing ...'], expand_x = True, key = '-EDT-ASSETS-')]
                    ], expand_x = True)],
              [sg.Push(), sg.Button ('Save & Close')]]

    _win = sg.Window ('Edit note', layout, modal = True, finalize = True, resizable = True,
                      icon = assets['win_ico'])
    push_nested_window (_win, True)

    _win.bind ('<Escape>', 'ESC')

    while True: # Event Loop
        event, values = _win.read()
        #if event not in (None, sg.TIMEOUT_KEY, '__TIMER EVENT__'):
        #    print (event)
        #    print (values)

        if event in (sg.WIN_CLOSED, 'Exit', 'ESC'):
            edit_note = note
            break
        if event == 'Save & Close':
            edit_note = None
            break

    pop_nested_window (_win)
        
    return edit_note

def make_theme_window (theme):
    sg.theme (theme)

    layout = [[sg.Text('Theme Browser')],
              [sg.Listbox(values=sg.theme_list(), size=(20, 12), key='-LIST-', enable_events = True, select_mode = "LISTBOX_SELECT_MODE_SINGLE")],
              [sg.Button('OK'), sg.Button('Exit')]]

    _win = sg.Window('Theme Browser', layout, modal = True, finalize = True,
                     icon = assets['win_ico'])
    push_nested_window (_win, True)
    return _win

def theme_change (cfg):
    global window

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
                pop_nested_window (setting_window)
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

    pop_nested_window (setting_window)

    if new_theme != old_theme:
        pop_nested_window (window)
        window = create_gui (new_theme)
        cfg['Appearance']['e'] = new_theme

    return cfg

def collect_tags_labels (values):
    query = ''
    if len(values['-NESTED_LBL-']) > 0:
        select = ''
        for val in values ['-NESTED_LBL-']:
            select += ',' + '/'.join(val.split('-lbl-'))[1:]
        query += 'labels ' + select [1:]

    if len (values['-TAGS-']) > 0:
        select = ''
        for val in values ['-TAGS-']:
            select += ',' + val.split(' ')[0]
        query += ('& ' if query != '' else '') + 'tags ' + select [1:]

    return query

def check_resize_cardbox ():
    # If cardbox was changed size, trigger refresh cardbox view
    cardbox_width = window[cardbox.name].get_size ()[0]
    if abs (cardbox_width - (cardbox.width + 15)) > 256:
        window.write_event_value (cardbox.name, cardbox_width)

dragging    = False
start_point = None
drag_fig    = None
lastxy      = None
snap_lastxy = None

def handle (cb):
    global dragging, start_point, drag_fig, lastxy, snap_lastxy

    event, values = window.read(100)
    graph = window [(cardbox.name, "graph")]

    #if event not in (None, sg.TIMEOUT_KEY, '__TIMER EVENT__'):
    #    print (event)
    #    print (values)

    if event == ' Resize':
        check_resize_cardbox ()
        return True

    if event in ('-NESTED_LBL-', '-TAGS-'):
        window['-SEARCH-'].update (value = 'Search query')
        query = collect_tags_labels (values)
        #print (query)
        if query != '':
            cardbox.filter (query)
        return True

    if event == '-SEARCH-':
        #print (values["-SEARCH-"])
        window['-TAGS-'].update (set_to_index = None)
        cardbox.filter (values["-SEARCH-"])
        return True

    if event == '-SEARCH-+INPUT FOCUS+':
        window['-SEARCH-'].update (value = '')
        return True

    if event == 'Settings::menu':
        cb['settings'] ()
        return True

    if event == 'Open::menu':
        cb['open'] ()
        return True

    if event == 'Delete::fig_menu':
        cb['note'] (cmd = 'delete')
        return True

    if event == 'Add tags::fig_menu':
        root_location = (graph.widget.winfo_rootx(), graph.widget.winfo_rooty())
        cb['note'] (cmd = 'tags', location = (values[(cardbox.name, 'graph')][0] + root_location[0],
                                              values[(cardbox.name, 'graph')][1] + root_location[1]))
        return True

    if event == 'Color::fig_color':
        root_location = (graph.widget.winfo_rootx(), graph.widget.winfo_rooty())
        cb['note'] (cmd = 'color', location = (values[(cardbox.name, 'graph')][0] + root_location[0],
                                               values[(cardbox.name, 'graph')][1] + root_location[1]))
        return True

    if event == '-BTN-REFRESH-':
        cardbox.notebook.Refresh ()
        update_show_tags         (cardbox.notebook.tags)
        update_show_labels       (cardbox.notebook.labels)
        cardbox.sync_cards       ()
        cardbox.refresh_box      ()
        return True

    if event == '-BTN-NOTE-':
        note = cb['new_note'] ()
        #print (note)
        if note is not None:
            update_show_tags         (cardbox.notebook.tags)
            update_show_labels       (cardbox.notebook.labels)
            cardbox.sync_cards       ()
            cardbox.refresh_box      ()

        return True

    if event == (cardbox.name, "graph"): # a mouse event on cardbox
        x, y = values [event]
        if not dragging:
            drag_fig = graph.get_figures_at_location ((x,y))[-2:]
            #print (drag_fig)
            if len(drag_fig) > 0:
                start_point = (x, y)
                dragging = True
                snap_lastxy = lastxy = x, y
        else:
            dx, dy = x - lastxy [0], y - lastxy [1]
            snap_dx, snap_dy = x - snap_lastxy [0], y - snap_lastxy [1]
            if abs(dx) > 2 or abs(dy) > 2:
                for fig in drag_fig:
                    graph.bring_figure_to_front (fig)
                    graph.move_figure (fig, dx, dy)
                graph.update ()
                lastxy = x, y

                if abs(snap_dx) > 10 or abs(snap_dy) > 10:
                    dest_fig = graph.get_figures_at_location ((x,y))[:2]
                    cardbox.swap (drag_fig, dest_fig)
                    snap_lastxy = x, y

        return True

    if event == ((cardbox.name, 'graph'), '+UP'):
        if dragging:
            dest_fig = graph.get_figures_at_location (lastxy)[:2]
            cardbox.swap (drag_fig, dest_fig, always_refresh = True)

        dragging    = False
        drag_fig    = None
        start_point = None
        lastxy      = None
        snap_lastxy = None
        return True

    if event in (None, sg.WINDOW_CLOSED, 'Exit'):
        return False

    if event == cardbox.name:
        cardbox.resize (values ['cardbox'])
        return True

    # Check periodically
    check_resize_cardbox ()

    # Call sub-components's handles
    cal.handle (event, values)
    return True
