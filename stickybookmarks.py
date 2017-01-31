import sublime, sublime_plugin
import os, re, pickle

#sbmarks dict structure:
#{filepath: {lineno: linetext, lineno: linetext, ...}, ...}

class StickyBookmarksEvents(sublime_plugin.EventListener):
    def on_pre_close(self, view):
        sublime.active_window().run_command("sticky_bookmarks", {"action": "on_pre_close", "view": view.id()})

    def on_load_async(self, view):
        sublime.active_window().run_command("sticky_bookmarks", {"action": "on_load_async", "view": view.id()})

class StickyBookmarks(sublime_plugin.WindowCommand):
    #basic functions
    def __init__(self, window):
        self.window = window
        self.load();

    def load(self):
        self.sbmarks = {}
        if not "project" in self.window.extract_variables():
            return
        path=self.window.extract_variables()["project"]+".sbmarks"
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                # The protocol version used is detected automatically, so we do not
                # have to specify it.
                self.sbmarks = pickle.load(f)
        print(self.sbmarks)

    def save(self):
        print(self.sbmarks)
        if not "project" in self.window.extract_variables():
            return
        path=self.window.extract_variables()["project"]+".sbmarks"
        print(path)
        with open(path, 'wb') as f:
            pickle.dump(self.sbmarks, f, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def get_line(view, region):
        line=view.line(region.a)
        return view.substr(line)

    def find_best_match(self, view, lineno, linetext):
        matches = view.find_all(linetext, sublime.LITERAL)
        bestmatch = None
        bestmatchScore = -1
        for match in matches:
            if StickyBookmarks.get_line(view, match) == linetext:
                l, _ = view.rowcol(match.a)
                l = abs(l-lineno)
                if l < bestmatchScore:
                    bestmatchScore = l
                    bestmatch = match
        return match

    #events
    def on_pre_close(self, view):
        if not view:
            return
        filename = view.file_name()
        if not filename:
            return
        bmarks = {}
        regs = view.get_regions("bookmarks")
        if len(regs) == 0 and filename in self.sbmarks:
            del self.sbmarks[filename]
        else:
            for r in regs:
                lineno,_ = view.rowcol(r.a)
                linetext = StickyBookmarks.get_line(view, r)
                bmarks[lineno] = linetext
            self.sbmarks[filename] = bmarks
        self.save()
        print(self.sbmarks)

    def on_load_async(self, view):
        filename = view.file_name()
        if (not filename) or (filename not in self.sbmarks):
            return
        view.erase_regions("bookmarks")
        bmarks = self.sbmarks[filename]
        print(bmarks)
        regions = []
        for lineno, linetext in bmarks.items():
            r = self.find_best_match(view, lineno, linetext)
            if r:
                regions.append(sublime.Region(r.a, r.a))
        view.add_regions("bookmarks", regions, scope="bookmark", icon="bookmark", flags=sublime.HIDDEN)

    #commands
    def clearfile(self):
        view = self.window.active_view()
        view.clear_regions("bookmarks")
        fn = view.file_name()
        if fn and (fn in self.sbmarks):
            del self.sbmarks[fn]
        self.save()

    def clearall(self):
        for view in self.window.views():
            view.clear_regions("bookmarks")
        self.sbmarks = {}
        self.save()

    def listbookmarks(self):
        locations=[]
        def go_there(i):
            print(locations)
            if i < 0 or i >= len(locations):
                return
            selected = locations[i]
            print(selected[0])
            if type(selected[0]) is str:
                filename, row = selected
                self.window.open_file(filename+":"+str(row+1), sublime.ENCODED_POSITION)
            else:
                view, region = selected
                self.window.focus_view(view)
                view.show_at_center(region)
                view.sel().clear()
                view.sel().add(region)

        items=[]
        for view in self.window.views():
            prefix=""
            if view.name():
                prefix=view.name()+":"
            elif view.file_name():
                prefix=os.path.basename(view.file_name())+":"
            for region in view.get_regions("bookmarks"):
                row,_=view.rowcol(region.a)
                line=re.sub('\s+', ' ', view.substr(view.line(region))).strip()
                items.append(prefix+str(row+1)+": "+line)
                locations.append((view, region))
        for filename, bms in self.sbmarks.items():
            print(filename)
            if not self.window.find_open_file(filename):
                prefix=os.path.basename(filename)+":"
                for row in sorted(bms):
                    line=re.sub('\s+', ' ', bms[row]).strip()
                    items.append(prefix+str(row+1)+": "+line)
                    locations.append((filename, row))
        if len(items) > 0:
            self.window.show_quick_panel(items, go_there, sublime.MONOSPACE_FONT)
        else:
            sublime.status_message("No bookmarks found")

    def get_view(self, id):
        for v in self.window.views():
            if v.id() == id:
                return v

    def run(self, action, view = 0):
        if action == "clearfile":
            self.clearfile()
        elif action == "clearall":
            self.clearall()
        elif action == "list":
            self.listbookmarks()
        elif action == "on_pre_close":
            self.on_pre_close(self.get_view(view))
        elif action == "on_load_async":
            self.on_load_async(self.get_view(view))
