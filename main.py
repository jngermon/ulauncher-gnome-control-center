import os
import json
import logging
import subprocess
import distutils.spawn
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.item.SmallResultItem import SmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction


logging.basicConfig()
logger = logging.getLogger(__name__)

# Initialize items cache and gnome-control-center path
items_cache = []
global usage_cache
usage_cache = {}

# Usage tracking
script_directory = os.path.dirname(os.path.realpath(__file__))
usage_db = os.path.join(script_directory, 'usage.json')
if os.path.exists(usage_db):
    with open(usage_db, 'r') as db:
        # Read JSON string
        raw = db.read()
        # JSON to dict
        usage_cache = json.loads(raw)

gcpath = ''
# Locate gnome-control-center
gcpath = distutils.spawn.find_executable('gnome-control-center')
# This extension is useless without gnome-control-center
if gcpath is None or gcpath == '':
    logger.error('gnome-control-center path could not be determined')
    exit()


class GnomeControlExtension(Extension):
    def __init__(self):
        panels = []
        try:
            # Get list of panel names from gnome-control-center
            panel_list = subprocess.check_output(["env", "XDG_CURRENT_DESKTOP=GNOME", gcpath, "--list"])
            # Get sorted list of panels without empty items and without
            # irrelevant help text
            panels = sorted([i.strip() for i in panel_list.split('\n')
                             if not i.startswith("Available") and len(i) < 1])
        except Exception as e:
            print('Failed getting panel names, fallback to standard names')
        # Load default panels if they could not be retrieved
        if len(panels) < 2:
            panels = ['background',
                      'bluetooth',
                      'color',
                      'datetime',
                      'display',
                      'info-overview',
                      'default-apps',
                      'removable-media',
                      'keyboard',
                      'mouse',
                      'network',
                      'wifi',
                      'notifications',
                      'online-accounts',
                      'power',
                      'printers',
                      'privacy',
                      'region',
                      'search',
                      'sharing',
                      'sound',
                      'universal-access',
                      'user-accounts',
                      'wacom']

        for p in panels:
            # Capitalize words to form item title
            title = " ".join(w.capitalize() for w in p.split('-'))
            items_cache.append(create_item(title, p, p, title, p))

        super(GnomeControlExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        # Get query
        term = (event.get_argument() or '').lower()

        items = []

        # Display all items when query empty
        if term == "":
            items = sorted([i for i in items_cache],
                           key=sort_by_usage,
                           reverse=True)
        # Only display items containing query substring
        else:
            items = sorted([i for i in items_cache if term in i._name.lower()],
                           key=sort_by_usage,
                           reverse=True)
        return RenderResultListAction(items[:8])


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        global usage_cache
        # Get query
        data = event.get_data()
        b = data['id']
        # Check usage and increment
        if b in usage_cache:
            usage_cache[b] = usage_cache[b]+1
        else:
            usage_cache[b] = 1
        # Update usage JSON
        with open(usage_db, 'w') as db:
            db.write(json.dumps(usage_cache, indent=2))

        return RunScriptAction('#!/usr/bin/env bash\nenv XDG_CURRENT_DESKTOP=GNOME {} {}\n'.format(gcpath, b), None).run()


def create_item(name, icon, keyword, description, on_enter):
    return ExtensionResultItem(
            name=name,
            icon='images/{}.svg'.format(icon),
            on_enter=ExtensionCustomAction(
                 {'id': on_enter})
            )


def sort_by_usage(i):
    global usage_cache
    # Convert item name to ID format
    j = i._name.lower().replace(' ', '-')
    # Return score according to usage
    if j in usage_cache:
        return usage_cache[j]
    # Default is 0 (no usage rank / unused)
    return 0


if __name__ == '__main__':
    GnomeControlExtension().run()
