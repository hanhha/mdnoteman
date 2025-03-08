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

Nb = Notebook ()

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

def clean_up ():
    save_config ()

if __name__ == "__main__":
    Nb.Create_random_notes (num = 10)

    gui.window = create_gui (default_theme)

    gui.cardbox.add_cards (Nb.notes)
    gui.window.timer_start (200)

    while gui.handle (setting_cb = lambda : call_settings (), open_cb = call_open):
        pass

    clean_up ()
    gui.window.timer_stop_all ()
    gui.window.close()
