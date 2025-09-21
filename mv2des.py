import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import shutil
import subprocess

def get_installed_apps():
    paths = [
        '/usr/share/applications/',
        os.path.expanduser('~/.local/share/applications/')
    ]
    apps = []
    for path in paths:
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.endswith('.desktop'):
                    full_path = os.path.join(path, file)
                    mtime = os.path.getmtime(full_path)
                    with open(full_path, 'r') as f:
                        content = f.read()
                        name_start = content.find('Name=')
                        if name_start != -1:
                            name_end = content.find('\n', name_start)
                            name = content[name_start+5:name_end].strip()
                            apps.append((False, name, full_path, mtime))
    apps.sort(key=lambda x: x[1])  # Initial sort by name
    return apps

class AppSelector(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Add App Shortcuts to Desktop")
        self.set_default_size(400, 300)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        # Search entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search apps...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        vbox.pack_start(self.search_entry, False, False, 0)

        # Sort combo
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        label = Gtk.Label(label="Sort by:")
        hbox.pack_start(label, False, False, 0)
        self.sort_combo = Gtk.ComboBoxText()
        self.sort_combo.append_text("Name (A-Z)")
        self.sort_combo.append_text("Newest First")
        self.sort_combo.set_active(0)
        self.sort_combo.connect("changed", self.on_sort_changed)
        hbox.pack_start(self.sort_combo, False, False, 0)
        vbox.pack_start(hbox, False, False, 0)

        self.liststore = Gtk.ListStore(bool, str, str, float)  # selected, name, path, mtime
        for app in get_installed_apps():
            self.liststore.append(app)

        self.filter_model = self.liststore.filter_new()
        self.filter_model.set_visible_func(self.filter_func)
        self.search_text = ""

        self.treeview = Gtk.TreeView(model=self.filter_model)

        # Checkbox column
        toggle_renderer = Gtk.CellRendererToggle()
        toggle_renderer.connect("toggled", self.on_toggle)
        toggle_column = Gtk.TreeViewColumn("Select", toggle_renderer, active=0)
        self.treeview.append_column(toggle_column)

        # Name column
        text_renderer = Gtk.CellRendererText()
        text_column = Gtk.TreeViewColumn("App Name", text_renderer, text=1)
        self.treeview.append_column(text_column)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.treeview)
        vbox.pack_start(scrolled_window, True, True, 0)

        button = Gtk.Button(label="Add Selected to Desktop")
        button.connect("clicked", self.on_add_clicked)
        vbox.pack_start(button, False, False, 0)

    def filter_func(self, model, iter, data):
        if not self.search_text:
            return True
        return self.search_text.lower() in model[iter][1].lower()

    def on_search_changed(self, entry):
        self.search_text = entry.get_text()
        self.filter_model.refilter()

    def on_sort_changed(self, combo):
        sort_type = combo.get_active_text()
        if sort_type == "Name (A-Z)":
            self.liststore.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        elif sort_type == "Newest First":
            self.liststore.set_sort_column_id(3, Gtk.SortType.DESCENDING)

    def on_toggle(self, widget, path):
        # Convert filter path to liststore path
        filter_path = Gtk.TreePath(path)
        filter_iter = self.filter_model.get_iter(filter_path)
        liststore_iter = self.filter_model.convert_iter_to_child_iter(filter_iter)
        self.liststore[liststore_iter][0] = not self.liststore[liststore_iter][0]

    def on_add_clicked(self, button):
        for row in self.liststore:
            if row[0]:
                path = row[2]
                desktop_path = os.path.expanduser('~/Desktop/')
                dest_file = os.path.join(desktop_path, os.path.basename(path))
                shutil.copy(path, dest_file)
                os.chmod(dest_file, 0o755)
                subprocess.call(['gio', 'set', dest_file, 'metadata::trusted', 'true'])
                print(f"Copied, made executable, and trusted: {dest_file}")
                row[0] = False  # Reset checkbox

if __name__ == "__main__":
    win = AppSelector()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
