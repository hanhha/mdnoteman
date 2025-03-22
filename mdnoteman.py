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
else:
    cfg['Appearance'] = {'Theme': 'SystemDefault1'}
    cfg['Notebook'] = {'Path': ''}

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
    #print (notes)
    if kwargs['cmd'] == 'color':
        l = len (notes)
        color = notes[0].note.color [1:] if l == 1 else None
        new_color = gui.call_color_chooser_window (color = color, location = kwargs['location'])
        gui.cardbox.change_note_color (notes, '#' + new_color)
        return True
    if kwargs['cmd'] == 'delete':
        gui.cardbox.delete_note (notes)
        gui.update_show_tags    (Nb.tags)
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

    gui.window = create_gui (default_theme)

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
    gui.pop_nested_window (purge = True)
