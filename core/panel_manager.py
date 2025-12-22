import json, os, uuid

PANELS_FILE = "config/panels.json"

def load_panels():
    if not os.path.exists(PANELS_FILE):
        return {}
    return json.load(open(PANELS_FILE))

def save_panels(data):
    json.dump(data, open(PANELS_FILE, "w"), indent=2)

def create_panel(data):
    panels = load_panels()
    panel_id = "PANEL_" + uuid.uuid4().hex[:6].upper()
    panels[panel_id] = data
    save_panels(panels)
    return panel_id

def remove_panel(panel_id):
    panels = load_panels()
    if panel_id in panels:
        del panels[panel_id]
        save_panels(panels)
        return True
    return False
