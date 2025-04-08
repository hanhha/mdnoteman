#!/usr/bin/env python

import sys
if sys.hexversion < 0x03070000:
    print("!!! This component requires Python version 3.7 at least !!!")
    sys.exit(1)

import markdown
import FreeSimpleGUI as sg
import tkinter as tk
import base64
import re
import time

from fsg_calendar import Calendar
from tkhtmlview import html_parser
from mdnoteman_pkm import Note, Notebook, CardBox
from dataclasses import dataclass, field
from typing import List, Dict, Set
from copy import copy

debug = False
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

def flush_events ():
    global window_stack

    if len(window_stack) > 0:
        window_stack[-1][0].read ()

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
        if len(window_stack) > 0:
            window_stack[-1][0].read (10) # Flush event read before back to previous window

def set_html (widget, html, strip = True):
    parser = html_parser.HTMLTextParser()
    prev_state = widget.cget('state')
    widget.config(state=sg.tk.NORMAL)
    widget.delete('1.0', sg.tk.END)
    widget.tag_delete(widget.tag_names)
    parser.w_set_html(widget, html, strip=strip)
    widget.config(state=prev_state)

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
                                     num_rows = 10,
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
                                                                size = (None, 2), write_only = True,
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
    win.set_min_size ((lwidth + rwidth + 280, 480))

    #win.bind ("<ButtonPress-1>", ' Press')
    #win.bind ("<ButtonRelease-1>", ' Release')
    win.bind ("<Configure>", ' Resize')
    win['-SEARCH-'].bind ("<Return>", "")
    win['-SEARCH-'].bind ('<FocusIn>', '+INPUT FOCUS+')
    win['-SEARCH-'].bind ('<FocusOut>', '-INPUT FOCUS-')
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

def create_gui (cfg, label_tree = None):
    global cal
    global cardbox

    theme = cfg ['Appearance']['Theme']

    sg.theme(theme)
    font = ("default", 15, 'normal')
    sg.set_options(font=font)
    window = make_main_window (cal, label_tree = label_tree)
    cal.init_cal (window)
    cardbox.init (window = window, container_scroll_cb = window[cardbox.name].TKColFrame.yscroll, cfg = cfg)

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
            cb.append ([sg.pin(sg.Checkbox(tag, key = tag, expand_x = True, default = tag in selected_tags),
                               shrink = True)])
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
    push_nested_window (_win, True)
    _win.bind ('<FocusOut>', 'LostFocus')
    _win.bind ('<Escape>', 'ESC')
    _win['-IN-'].bind('<Return>', 'Enter')

    tags_inp = []
    if isinstance (selected_tags, list):
        new_tags = selected_tags
    else:
        new_tags = list(selected_tags)
    input_txt = ''

    while True:
        event, values = _win.read (100)
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

            new_tags = []
            for k in tags.keys():
                if values[k]:
                    new_tags.append (k)
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
    return set(new_tags) != set(selected_tags), set(new_tags)

def call_color_chooser_window (color = None, location = None):
    color_dict = {}
    color_dict ['White']        = '#FFFFFF'
    color_dict ['Pink']         = '#FF69B4'
    color_dict ['Gray']         = '#ABABAB'
    color_dict ['Yellow']       = '#FFFF00'
    color_dict ['Light Blue']   = '#87CEFA'
    color_dict ['Light Green']  = '#90EE90'
    color_dict ['Light Purple'] = '#9370DB'

    prev = {}
    prev ['#FFFFFF'] = False
    prev ['#FF69B4'] = False
    prev ['#ABABAB'] = False
    prev ['#FFFF00'] = False
    prev ['#87CEFA'] = False
    prev ['#90EE90'] = False
    prev ['#9370DB'] = False

    cb = []
    for k,v in color_dict.items():
        cb.append ([sg.Checkbox(k, key = v, background_color = v, expand_x = True)])

    _win = sg.Window ('', layout = cb, modal = True,
                      no_titlebar = True,
                      keep_on_top = True, location = (location[0], location[1] - 32),
                      finalize = True, icon = assets['win_ico'],
                      resizable = False)
    push_nested_window (_win, True)
    _win.bind ('<FocusOut>', 'LostFocus')
    _win.bind ('<ButtonRelease-1>', 'Release')
    _win.bind ('<Escape>', 'ESC')

    selected = color
    if color is not None:
        _win[color].update (value = True)
        prev[color] = True

    while True:
        event, values = _win.read (100)
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
    if note:
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

    existed_tags = copy(cardbox.notebook.tags)
    existed_lbls = copy(cardbox.notebook.labels_flatten)

    md_layout = [[sg.Multiline (key = '-EDT-NOTE-', expand_x = True, expand_y = True,
                                default_text = ctn,
                                size = (80, 10),
                                right_click_menu = [[''], ['Copy::menu', 'Paste::menu', 'Cut::menu']],
                                enable_events = True,
                                do_not_clear = True)]]
    preview_layout = [[sg.Multiline (key = '-VIEW-NOTE-', expand_x = True, expand_y = True,
                                     size = (80, 10),
                                     disabled = True)]]

    layout = [[sg.TabGroup([[sg.Tab('Markdown', md_layout, tooltip = 'Markdown format', key = '-EDT-TAB-'),
                             sg.Tab('Preview', preview_layout, tooltip = 'Preview', key = '-VIEW-TAB-')]], expand_x = True, expand_y = True, enable_events = True)],
              [sg.Button (key = '-BTN-COLOR-', border_width = 1, image_source = assets['color_ico'],
                          button_color = (color, color),
                          image_subsample = 15, tooltip = "Change background color of note"),
               sg.Button ('Add labels'),
               sg.Button ('Add tags'),
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
                      icon = assets['win_ico'], keep_on_top = True)
    push_nested_window (_win, True)

    _win.bind ('<Escape>', 'ESC')
    _win['-EDT-NOTE-'].bind ('<FocusIn>', '+INPUT FOCUS+')
    _win['-EDT-NOTE-'].bind ('<FocusOut>', '-INPUT FOCUS-')

    ctn_edited  = True if note is not None else False
    note_delete = False

    while True: # Event Loop
        event, values = _win.read(100)
        #if event not in (None, sg.TIMEOUT_KEY, '__TIMER EVENT__'):
        #    print (event)
        #    print (values)

        if event == 0 and values[0] == '-VIEW-TAB-':
            #print (markdown.markdown (values['-EDT-NOTE-']))
            set_html (_win['-VIEW-NOTE-'].Widget, markdown.markdown (values['-EDT-NOTE-']))
            continue

        if event == '-EDT-NOTE-':
            ctn_edited = True
            continue

        if event == '-EDT-NOTE-+INPUT FOCUS+':
            if ctn_edited == False:
                _win['-EDT-NOTE-'].update (value = '')
            continue

        if event == '-EDT-NOTE--INPUT FOCUS-':
            if ctn_edited == False or values['-EDT-NOTE-'].strip() == '':
                ctn_edited = False
                _win['-EDT-NOTE-'].update (value = 'Take a note in MD format ...')
            continue

        if event == '-BTN-DEL-':
            note_delete = True
            edit_note   = None
            break

        if event == '-BTN-COLOR-':
            root_location = (_win['-BTN-COLOR-'].widget.winfo_rootx(), _win['-BTN-COLOR-'].widget.winfo_rooty())
            new_color = call_color_chooser_window (color = color, location = root_location)
            if new_color:
                color = new_color
                _win['-BTN-COLOR-'].update (button_color = color)
            continue

        if event == 'Add tags':
            root_location = (_win['Add tags'].widget.winfo_rootx(), _win['Add tags'].widget.winfo_rooty())
            changed, new_tags = call_tags_chooser_window ("Tag note", tags = existed_tags, selected_tags = tags,
                                                 location = root_location, relax_list_order = True, row_limit = 8)
            if changed:
                if new_tags:
                    for t in new_tags:
                        if t not in existed_tags:
                            existed_tags [t] = 1
                        else:
                            if t not in tags:
                                existed_tags [t] += 1

                    tags = new_tags
                else:
                    tags = []
            continue

        if event == 'Add labels':
            root_location = (_win['Add labels'].widget.winfo_rootx(), _win['Add labels'].widget.winfo_rooty())
            changed, new_labels = call_tags_chooser_window ("Label note", tags = existed_lbls, selected_tags = labels,
                                             location = root_location, relax_list_order = False)
            if changed:
                if new_labels:
                    for l in new_labels:
                        if l not in existed_lbls:
                            existed_lbls [l] = 1
                        else:
                            if l not in lbls:
                                existed_lbls [l] += 1

                    labels = new_labels
                else:
                    labels = []
            continue

        if event in (sg.WIN_CLOSED, 'ESC'):
            edit_note = None
            break

        if event == 'Save & Close':
            edit_note = Note (timestamp = int(time.time()), content = values ['-EDT-NOTE-'] if ctn_edited else '', tags = tags, labels = labels, links = links, color = color)
            break

    pop_nested_window (_win)
        
    return note_delete, edit_note

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
        event, values  = setting_window.read(100)
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
in_drag     = False

def handle (cb):
    global in_drag, dragging, start_point, drag_fig, lastxy, snap_lastxy

    event, values = window.read(100)
    graph = window [(cardbox.name, "graph")]

    #if event not in (None, sg.TIMEOUT_KEY, '__TIMER EVENT__'):
    #    print (event)
    #    print (values)

    if event == ' Resize':
        check_resize_cardbox ()
        return True

    if event in ('-NESTED_LBL-', '-TAGS-'):
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

    if event == '-SEARCH--INPUT FOCUS-':
        if values['-SEARCH-'].strip() == '':
            window['-SEARCH-'].update (value = 'Search query')
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

    if event == 'Add labels::fig_menu':
        root_location = (graph.widget.winfo_rootx(), graph.widget.winfo_rooty())
        cb['note'] (cmd = 'labels', location = (values[(cardbox.name, 'graph')][0] + root_location[0],
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
        delete, note = cb['new_note']()
        #print (note)
        if not delete and (note is not None):
            cardbox.notebook.add_note (note, set_dirty = True)
            update_show_tags    (cardbox.notebook.tags)
            update_show_labels  (cardbox.notebook.labels)
            cardbox.sync_cards  (dirty_only = True)
            cardbox.refresh_box ()
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
                in_drag = True or in_drag

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
        if lastxy is not None:
            dest_fig = graph.get_figures_at_location (lastxy)[:2]

            if in_drag:
                cardbox.swap (drag_fig, dest_fig, always_refresh = True)

            else: # Click only on note
                note = cardbox.find_note_at_fig (dest_fig)
                if note:
                    delete, edited = cb['new_note'](note = note)
                    if delete:
                        cardbox.update_note (cardbox.find_notes_from_fig (dest_fig), delete = True)
                        update_show_tags    (cardbox.notebook.tags)
                        update_show_labels  (cardbox.notebook.labels)
                    else:
                        if edited is not None:
                            cardbox.notebook.update_note (note, edited, set_dirty = True) 
                            cardbox.sync_cards  (dirty_only = True)
                            cardbox.refresh_box ()
                            update_show_tags    (cardbox.notebook.tags)
                            update_show_labels  (cardbox.notebook.labels)

        # Reset all 
        dragging    = False
        in_drag     = False
        drag_fig    = None
        start_point = None
        lastxy      = None
        snap_lastxy = None

        return True

    if event in (sg.WIN_CLOSED, 'Exit::menu'):
        return False

    if event == cardbox.name:
        cardbox.resize (values ['cardbox'])
        return True

    # Check periodically
    check_resize_cardbox ()

    # Call sub-components's handles
    cal.handle (event, values)
    return True
