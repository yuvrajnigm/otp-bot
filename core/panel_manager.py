import json, os, uuid

PANELS_FILE = "config/panels.json"

def load_panels():
    if not os.path.exists(PANELS_FILE):
        return {}
    with open(PANELS_FILE) as f:
        return json.load(f)

def save_panels(panels):
    with open(PANELS_FILE, "w") as f:
        json.dump(panels, f, indent=2)

def create_panel(panel_data):
    panels = load_panels()
    pid = "PANEL_" + uuid.uuid4().hex[:6].upper()
    panel_data["enabled"] = True
    panels[pid] = panel_data
    save_panels(panels)
    return pid

def remove_panel(pid):
    panels = load_panels()
    if pid in panels:
        del panels[pid]
        save_panels(panels)
        return True
    return False
