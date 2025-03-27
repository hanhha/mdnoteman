#!/usr/bin/env python

import sys
if sys.hexversion < 0x03050000:
    print("!!! This component requires Python version 3.5 at least !!!")
    sys.exit(1)

import configparser
from pathlib import Path

import FreeSimpleGUI as sg
import mdnoteman_gui as gui
from mdnoteman_pkm import Notebook

cfgpath_str = str(Path.home ()) + "/.mdnote"
cfgfile_str = cfgpath_str + '/config'
cfg = configparser.ConfigParser ()
cfg_file = Path(cfgfile_str)
if cfg_file.exists() and cfg_file.is_file():
    cfg.read (cfgfile_str)

dflt_cfg = {}
dflt_cfg['Appearance'] = {'Theme': 'SystemDefault1'}
dflt_cfg['Notebook'] = {'Path': ''}

if sys.platform == 'linux':
    font_path = '' # TODO
elif sys.platform == 'darwin':
    font_path = str(Path.home()) + "/Library/Fonts/"
elif sys.platform == 'win32':
    font_path = '' # TODO
else:
    font_path = '' # TODO

dflt_cfg['Fonts'] = {'Bold':   font_path + "/FreeSansBold.otf"
                    ,'Code':   font_path + "/FreeMono.otf"
                    ,'Dflt':   font_path + "/FreeSans.otf"
                    ,'Italic': font_path + "/FreeSansOblique.otf"
                    ,'Code_size' : 14
                    ,'Size':   12}

def add_dict (a, b):
    for k in b:
        if k not in a:
            a [k] = b [k]
        else:
            if b [k] is dict:
                a [k] = add_dict (a [k], b [k])
    return a

cfg = add_dict (cfg, dflt_cfg)

default_theme = cfg ['Appearance']['Theme']

Nb = Notebook (path = cfg['Notebook']['Path'])

def save_config ():
    global cfgpath_str
    global cfg

    Path(cfgpath_str).mkdir (parents = True, exist_ok = True)
    with open (cfgpath_str + '/config', 'w') as cfgfile:
        cfg.write (cfgfile)

def new_notebook (path):
    global Nb

    Nb = Notebook (path = path)
    Nb.Refresh ()

def call_note (**kwargs):
    notes = gui.cardbox.find_notes_from_fig (gui.window[(gui.cardbox.name, 'graph')].selected_fig)
    gui.window[(gui.cardbox.name, 'graph')].selected_fig = None

    #print (notes)
    if kwargs['cmd'] == 'color':
        l = len (notes)
        color = notes[0].note.color [1:] if l == 1 else None
        new_color = gui.call_color_chooser_window (color = color, location = kwargs['location'])
        gui.cardbox.update_note (notes, color = new_color)
        return True

    if kwargs['cmd'] == 'delete':
        gui.cardbox.update_note (notes, delete = True)
        gui.update_show_tags    (Nb.tags)
        gui.update_show_labels  (Nb.labels)
        return True

    if kwargs['cmd'] == 'tags':
        l = len (notes)
        tags          = gui.cardbox.notebook.tags
        selected_tags = notes[0].note.tags if l == 1 else []
        new_tags      = gui.call_tags_chooser_window ("Tag note", tags = tags, selected_tags = selected_tags,
                                                      location = kwargs['location'], relax_list_order = True, row_limit = 8)
        gui.cardbox.update_note (notes, tags = new_tags)
        gui.update_show_tags    (Nb.tags)
        return True

    if kwargs['cmd'] == 'labels':
        l = len (notes)
        lbls          = gui.cardbox.notebook.labels_flatten
        selected_lbls = notes[0].note.labels if l == 1 else []
        new_labels    = gui.call_tags_chooser_window ("Label note", tags = lbls, selected_tags = selected_lbls,
                                                      location = kwargs['location'], relax_list_order = False)
        gui.cardbox.update_note (notes, labels = new_labels)
        gui.update_show_labels  (Nb.labels)
        return True

def call_open ():
    global cfg

    sel_notebook = sg.popup_get_folder (message = 'Select path to notebook',
                                        default_path = cfg['Notebook']['Path'],
                                        initial_folder = str(Path.home()), grab_anywhere = True, keep_on_top = True) \
                   or cfg['Notebook']['Path']
    if sel_notebook != cfg['Notebook']['Path']:
        cfg['Notebook']['Path'] = sel_notebook
    save_config ()
    new_notebook (sel_notebook)

def create_gui (theme):
    global Nb

    return gui.create_gui (theme, label_tree = Nb.labels)

def call_settings ():
    global cfg

    cfg = gui.theme_change (cfg)
    save_config ()

def call_new_note ():
    note = gui.call_edit_window ()

def clean_up ():
    global Nb

    save_config ()
    Nb.Refresh ()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'debug':
            gui.debug = True

    #Nb.Create_random_notes (num = 10)
    if cfg['Notebook']['Path'] != '':
        Nb.Refresh ()

    gui.window = create_gui (cfg)

    gui.cardbox.set_notebook (Nb)
    gui.update_show_tags     (Nb.tags)
    gui.update_show_labels   (Nb.labels)

    cb = {'settings': call_settings,
          'open'    : call_open,
          'note'    : call_note,
          'new_note': call_new_note,
          }
    while gui.handle (cb = cb):
        pass

    clean_up ()
