

import sys, os, traceback, thread
import wx
import wx.py.crust
import wx.html
import pydia

try:
    from agw import aui
except ImportError: # if it's not there locally, try the wxPython lib.
    import wx.lib.agw.aui as aui

assertMode = wx.PYAPP_ASSERT_DIALOG

class Log:
    def WriteText(self, text):
        if text[-1:] == '\n':
            text = text[:-1]
        wx.LogMessage(text)
    write = WriteText

#---------------------------------------------------------------------------

class TreeData(object):

    SEARCH = "search"
    SYMBOL = "symbol"
    
    def GetTreeDataType(self):
        raise NotImplementedError("TreeData.GetTreeDataType")


class FindChildrenData(TreeData):
    def __init__(self):
        self.name = ""
        self.type = pydia.SYMTAG.SymTagNull
        self.flags = pydia.NameSearchOptions.nsNone
        self.busy = False

    def GetTreeDataType(self):
        return TreeData.SEARCH

    def GetTitle(self):
        return "Find children... [{}]".format(",".join(self.GetOptions()))

    def GetOptions(self):
        opt = []
        if self.name or self.type or self.flags:
            opt.append(self.name)
            if self.type:
                opt.append(pydia.SYMTAG_name(self.type))
            for k in pydia.NameSearchOptions.__dict__.keys():
                if k.startswith("ns") and (self.flags & getattr(pydia.NameSearchOptions, k)):
                    opt.append(k)
        return opt

    def GetNewOptions(self, parent):
        dlg = FindChildrenDialog(self, parent = parent, title = "Find children")
        result = dlg.ShowModal()
        if result == wx.ID_OK:
            self.name = dlg.GetName()
            self.type = dlg.GetType()
            self.flags = dlg.GetFlags()
        dlg.Destroy()
        return result


class SymbolData(TreeData):
    def __init__(self, session, symbol):
        assert session
        assert symbol
        self.session = session
        self.symbol = symbol

    def __del__(self):
        del self.symbol
        del self.session

    def GetTreeDataType(self):
        return TreeData.SYMBOL

    def GetTitle(self, text = None, attribute = False):
        symIndexId = self.symbol.symIndexId
        if text:
            return "{} - {}".format(symIndexId, text)
        symTagName = pydia.SYMTAG_name(self.symbol.symTag)
        name = self.symbol.name
        if attribute:
            return "{} - {} = {} , {}".format(symIndexId, attribute, symTagName, name)
        return "{} - {} , {}".format(symIndexId, symTagName, name)

#---------------------------------------------------------------------------

class FindChildrenDialog(wx.Dialog):
    def __init__(self, data, *args, **kwargs):
        wx.Dialog.__init__(self, *args, **kwargs)

        try:
            sizer = wx.BoxSizer(wx.VERTICAL)

            # name
            box = wx.BoxSizer(wx.HORIZONTAL)

            label = wx.StaticText(self, wx.ID_ANY, "Name :")
            box.Add(label, 0, wx.RIGHT, 5)

            self.name = wx.TextCtrl(self, wx.ID_ANY, "")
            self.name.SetValue(data.name)
            box.Add(self.name, 1, wx.EXPAND)

            sizer.Add(box, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            # type
            value = pydia.SYMTAG_name(data.type)
            choices = [k for k in pydia.SYMTAG.__dict__.keys() if k.startswith("SymTag")]
            assert value in choices
            
            box = wx.BoxSizer(wx.HORIZONTAL)

            label = wx.StaticText(self, wx.ID_ANY, "Type :")
            box.Add(label, 0, wx.RIGHT, 5)

            self.type = wx.ComboBox(self, value = value, choices = choices, style = wx.CB_READONLY)
            self.type.SetValue(value)
            box.Add(self.type, 1, wx.EXPAND)

            sizer.Add(box, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 5)

            # flags
            static = wx.StaticBox(self, wx.ID_ANY, label = "Flags :")

            box = wx.StaticBoxSizer(static, wx.VERTICAL)

            self.flags = dict()
            for flagname in sorted([k for k in pydia.NameSearchOptions.__dict__.keys() if k.startswith("ns")]):
                flag = getattr(pydia.NameSearchOptions, flagname)
                if flag:
                    check = wx.CheckBox(self, label = flagname, style = wx.CHK_2STATE)
                    if (flag & data.flags):
                        check.SetValue(True)
                    box.Add(check, 0, wx.ALIGN_LEFT)
                    self.flags[flagname] = check

            sizer.Add(box, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 5)

            # buttons
            btnsizer = wx.StdDialogButtonSizer()
            
            btn = wx.Button(self, wx.ID_OK)
            btn.SetDefault()
            btnsizer.AddButton(btn)

            btn = wx.Button(self, wx.ID_CANCEL)
            btnsizer.AddButton(btn)
            btnsizer.Realize()

            sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            self.SetSizer(sizer)
            sizer.Fit(self)
        except:
            traceback.print_exc()
            self.Destroy()

    def GetName(self):
        return self.name.GetValue()

    def GetType(self):
        return getattr(pydia.SYMTAG, self.type.GetValue())

    def GetFlags(self):
        flags = 0
        for flagname in self.flags.keys():
            if self.flags[flagname].GetValue():
                flags = flags | getattr(pydia.NameSearchOptions, flagname)
        return flags


class SymbolPanel(wx.Panel):
    def __init__(self, parent, session, symbol, log):
        wx.Panel.__init__(self, parent)
        try:
            assert session
            assert symbol
            self.log = Log()
            self.symIndexId = symbol.symIndexId

            sizer = wx.BoxSizer(wx.VERTICAL)

            # flags
            static = wx.StaticBox(self, label = "Metadata :")

            box = wx.StaticBoxSizer(static, wx.VERTICAL)

            metadata = pydia.SymbolPrinter(session).metadata(symbol)
            self.text = wx.TextCtrl(self, -1, value = '\n'.join(metadata), style = wx.TE_MULTILINE | wx.TE_READONLY)
            box.Add(self.text, 0, wx.EXPAND)
            
            sizer.Add(box, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
            
            self.SetSizer(sizer)
            sizer.Fit(self)
        except:
            traceback.print_exc()


class PyDiaGUI(wx.Frame):
    """DIA symbol viewer"""

    # File extensions for the Open dialog.
    wildcard = "All compatible types (*.pdb;*.exe;*.dll)|*.pdb;*.exe;*.dll|" \
               "Program database (*.pdb)|*.pdb|" \
               "Executable (*.exe)|*.exe|" \
               "Dynamic-link library (*.dll)|*.dll|" \
               "All files (*.*)|*.*"

    def __init__(self, parent = None, id = wx.ID_ANY, title = "PyDiaGUI", *args, **kwargs):
        super(PyDiaGUI, self).__init__(parent, id, title, *args, **kwargs)

        self.mgr = aui.AuiManager()

        # tell AuiManager to manage this frame
        self.mgr.SetManagedWindow(self)
        
        self.original_title = self.GetTitle()
        self.log = Log()
        self.session = None # PyDia
        self.sessionPages = []

        self.SetSize(wx.Size(800, 600))
        self.SetMinSize(wx.Size(400, 300))
        self.Centre()
        self.Show(True)
        
        # status bar
        self.statusbar = self.CreateStatusBar()

        try:
            self.MakeMenuBar()
            self.MakeToolBar()
            self.MakeShellPane()
            self.MakeSymbolTreePane()
            self.MakeSymbolBook()
            self.BindEvents()

            self.AddWelcomePage()
            self.statusbar.SetStatusText("Ready")
            self.DoUpdate()
        except:
            self.ShowExceptionInDialog()

    def OnOpen(self,event):
        dlg = wx.FileDialog(
            self, message = "Choose a file",
            defaultDir = os.getcwd(), 
            defaultFile = "",
            wildcard = self.wildcard,
            style = wx.OPEN | wx.CHANGE_DIR #| wx.MULTIPLE
            )
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            assert len(paths) == 1 # XXX we only support 1 for now

            for path in paths:
                self.statusbar.PushStatusText("Loading {}...".format(path))
                try:
                    self.OpenSession(path)
                except:
                    self.ShowExceptionInDialog()
                self.statusbar.PopStatusText()
        dlg.Destroy()
        self.statusbar.SetStatusText("Ready")

    def OnClose(self, evt):
        self.CloseSession()
        self.DoUpdate()

    def OnExit(self, event):
        self.CloseSession()
        self.Close(True)

    def OnHelp(self, event):
        self.AddWelcomePage()

    def OnAbout(self, evt):
        msg = ["Read the welcome page for more info.\n",
               "\n",
               "Author:\n",
               "  Flávio J. Saraiva <flaviojs2005@gmail.com>\n",
               "\n"
               "Please report any bugs or requests of improvements to:\n",
               "  https://github.com/flaviojs/pydia\n",
               "\n",
               "Using:\n",
               "  Python ", sys.version, "\n",
               "  wxPython ", wx.VERSION_STRING, "\n",
               ]
        msg = ''.join(msg)
        d = wx.MessageDialog(self, msg, "About", wx.OK)
        d.ShowModal()
        d.Destroy()

    def OnNotebookPageClose(self, event):
        book = self.mgr.GetPane("book").window
        page = book.GetPage(event.selection)
        try:
            self.sessionPages.remove(pane)
            pane.Hide()
            self.DoUpdate()
        except:
            pass

    def OnTreeItemExpanding(self, event):
        tree = self.mgr.GetPane("symboltree").window
        item = event.GetItem()
        assert item.IsOk()
        data = tree.GetPyData(item)
        if tree.ItemHasChildren(item) and tree.GetChildrenCount(item, False) == 0:
            if data.GetTreeDataType() == TreeData.SEARCH:
                self.SearchForChildren(item)
            elif data.GetTreeDataType() == TreeData.SYMBOL:
                self.FillSymbolTreeItem(item)

    def OnTreeItemActivate(self, event):
        tree = self.mgr.GetPane("symboltree").window
        item = event.GetItem()
        assert item.IsOk()
        image = tree.GetItemImage(item)
        data = tree.GetPyData(item)
        if data.GetTreeDataType() == TreeData.SEARCH:
            # search for children
            self.SearchForChildren(item)
        elif data: # symbol
            self.AddSymbolPage(data, tree.GetImageList().GetBitmap(image))
            self.DoUpdate()

    def DoUpdate(self):
        self.mgr.Update()
        self.Refresh()
        
    def MakeMenuBar(self):
        filemenu = wx.Menu()
        filemenu.Append(wx.ID_OPEN, "&Open...", "Open existing pdb/exe/dll file")
        filemenu.Append(wx.ID_CLOSE, "Close", "Close the active file")
        filemenu.Enable(wx.ID_CLOSE, False)
        filemenu.AppendSeparator()
        filemenu.Append(wx.ID_EXIT, "E&xit", "Terminate the program")

        helpmenu = wx.Menu()
        helpmenu.Append(wx.ID_HELP, "Welcome page", "Open welcome page")
        helpmenu.Append(wx.ID_ABOUT, "&About...", "Display program information")
        
        menubar = wx.MenuBar()
        menubar.Append(filemenu, "&File")
        menubar.Append(helpmenu, "&Help")
        self.SetMenuBar(menubar)

    def MakeToolBar(self):
        pass

    def MakeShellPane(self):
        return ## TODO figure out why it's hanging the app sometimes during load
        paneinfo = aui.AuiPaneInfo().Name("shell").Caption("Python Shell")
        paneinfo.Center().CloseButton(False).MaximizeButton(True).MinimizeButton(True).Hide()

        intro = 'Welcome To PyCrust %s' % wx.py.version.VERSION
        shell = wx.py.crust.Crust(self, intro = intro)
        #shell = wx.py.shell.Shell(self, intro = intro)
        self.mgr.AddPane(shell, paneinfo)

    def MakeSymbolBook(self):
        paneinfo = aui.AuiPaneInfo().Name("book").CenterPane().PaneBorder(False)
        ctrl = aui.AuiNotebook(self, agwStyle = aui.AUI_NB_DEFAULT_STYLE | aui.AUI_NB_TAB_EXTERNAL_MOVE | wx.NO_BORDER)
        self.mgr.AddPane(ctrl, paneinfo)

    def AddWelcomePage(self):
        book = self.mgr.GetPane("book").window
        
        image = wx.ArtProvider.GetBitmap(wx.ART_HELP_BOOK, wx.ART_OTHER, wx.Size(16, 16))
        htmlctrl = wx.html.HtmlWindow(book)
        htmlctrl.SetPage(GetIntroText())
        book.AddPage(htmlctrl, "Welcome page", False, image)

    def AddSymbolPage(self, data, bitmap = wx.NullBitmap):
        book = self.mgr.GetPane("book").window

        panel = SymbolPanel(book, data.session, data.symbol, self.log)
        caption = "Symbol #{}".format(data.symbol.symIndexId)
        book.AddPage(panel, caption, True, bitmap)
        self.sessionPages.append(panel)

    def MakeSymbolTreePane(self):
        paneinfo = aui.AuiPaneInfo().Name("symboltree").Caption("Symbol Tree")
        paneinfo.Bottom().CloseButton(False).MaximizeButton(True).MinimizeButton(True).Hide()
        
        imglist = wx.ImageList(16, 16, initialCount = 4)
        imglist.Add(wx.ArtProvider.GetBitmap(wx.ART_EXECUTABLE_FILE, wx.ART_OTHER, wx.Size(16, 16)))
        imglist.Add(wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16, 16)))
        imglist.Add(wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16, 16)))
        imglist.Add(wx.ArtProvider.GetBitmap(wx.ART_FIND, wx.ART_OTHER, wx.Size(16, 16)))
        self.TREE_ART_ROOT_SYMBOL       = 0 # root symbol, SymTagExe
        self.TREE_ART_ATTRIBUTE_SYMBOL  = 1 # attribute symbol
        self.TREE_ART_CHILD_SYMBOL      = 2 # child symbol
        self.TREE_ART_SEARCH_FILTER     = 3 # search filter

        tree = wx.TreeCtrl(self)
        tree.AssignImageList(imglist)
        self.mgr.AddPane(tree, paneinfo)

    def BindEvents(self):
        wx.EVT_MENU(self, wx.ID_OPEN, self.OnOpen)
        wx.EVT_MENU(self, wx.ID_CLOSE, self.OnClose)
        wx.EVT_MENU(self, wx.ID_EXIT, self.OnExit)
        wx.EVT_MENU(self, wx.ID_ABOUT, self.OnAbout)
        wx.EVT_MENU(self, wx.ID_HELP, self.OnHelp)

        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnNotebookPageClose)
        
        tree = self.mgr.GetPane("symboltree").window
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnTreeItemExpanding, tree)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeItemActivate, tree)

    def OpenSession(self, path):
        session = pydia.PyDia(path)
        self.CloseSession()
        self.session = session

        tree = self.mgr.GetPane("symboltree").Show().window
        symbol = self.session.globalScope
        image = self.TREE_ART_ROOT_SYMBOL
        data = SymbolData(session, symbol)
        root = tree.AddRoot(data.GetTitle(text = path), image)
        tree.SetPyData(root, data)
        self.FillSymbolTreeItem(root)
        tree.Expand(root)

        self.GetMenuBar().FindItemById(wx.ID_CLOSE).Enable(True)
        self.AddSymbolPage(data, tree.GetImageList().GetBitmap(image))
        self.DoUpdate()

    def CloseSession(self):
        del self.session
        self.session = None
        
        book = self.mgr.GetPane("book").window
        for page in self.sessionPages:
            book.DeletePage(book.GetPageIndex(page))
        del self.sessionPages[:]

        tree = self.mgr.GetPane("symboltree").Hide().window
        tree.DeleteAllItems()
            
        self.GetMenuBar().FindItemById(wx.ID_CLOSE).Enable(False)

    def ShowExceptionInDialog(self):
        desc = traceback.format_exc()
        dlg = wx.MessageDialog(self, desc, 'Error:', wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def SearchForChildren(self, item):
        assert item.IsOk()
        tree = self.mgr.GetPane("symboltree").window
        data = tree.GetPyData(item)
        assert data.GetTreeDataType() == TreeData.SEARCH
        if not data.busy and data.GetNewOptions(self) == wx.ID_OK:
            parent = tree.GetItemParent(item)
            assert parent.IsOk()
            symdata = tree.GetPyData(parent)
            assert symdata.GetTreeDataType() == TreeData.SYMBOL

            data.busy = True
            tree.SetItemText(item, "...(searching)... [{}]".format(','.join(data.GetOptions())))
            thread.start_new_thread(self._FindChildrenOfSymbol, (item, data, symdata))

    def _FindChildrenOfSymbol(self, item, data, symdata):
        """runs on worker thread"""
        assert item.IsOk()
        assert data.GetTreeDataType() == TreeData.SEARCH
        assert symdata.GetTreeDataType() == TreeData.SYMBOL

        name = data.name or None
        type = data.type
        flags = data.flags
        children = None
        try:
            # NOTE this can take a long time...
            children = list(symdata.session.findChildrenEx(symdata.symbol, type, name, flags))
        except:
            traceback.print_exc()
            children = []
        wx.CallAfter(self.AddChildrenToTree, item, symdata.session, children)

    def AddChildrenToTree(self, item, session, children):
        assert item.IsOk()
        tree = self.mgr.GetPane("symboltree").window
        tree.DeleteChildren(item)
        for child in children:
            data = SymbolData(session, child)
            childitem = tree.AppendItem(item, data.GetTitle(), self.TREE_ART_CHILD_SYMBOL)
            assert childitem.IsOk()
            tree.SetPyData(childitem, data)
            tree.SetItemHasChildren(childitem)
        data = tree.GetPyData(item)
        tree.SetItemText(item, data.GetTitle())
        tree.SetItemHasChildren(item, len(children) > 0)
        tree.Expand(item)
        tree.GetPyData(item).busy = False
        self.DoUpdate()

    def FillSymbolTreeItem(self, item):
        tree = self.mgr.GetPane("symboltree").window
        assert item
        assert item.IsOk()
        data = tree.GetPyData(item)

        # attribute symbols
        for attribute in pydia.SymbolPrinter(data.session).attributes(data.symbol):
            try:
                symbol = getattr(data.symbol, attribute)
                if symbol and type(symbol) == type(data.symbol):
                    image = self.TREE_ART_ATTRIBUTE_SYMBOL
                    data = SymbolData(data.session, symbol)
                    childitem = tree.AppendItem(item, data.GetTitle(attribute = attribute), image)
                    tree.SetPyData(childitem, data)
                    tree.SetItemHasChildren(childitem, True)
            except:
                pass

        # search filter
        image = self.TREE_ART_SEARCH_FILTER
        data = FindChildrenData()
        finditem = tree.AppendItem(item, data.GetTitle(), image)
        tree.SetPyData(finditem, data)
        tree.SetItemHasChildren(finditem, True)

#---------------------------------------------------------------------------

def GetIntroText():
    text = \
    "<html><body>" \
    "<h3>Welcome to PyDiaGUI</h3>" \
    "<p>Sections:</p>" \
    "<ol>" \
    "<li><a href='#overview'>Overview</a></li>" \
    "<li><a href='#instructions'>Instructions</a></li>" \
    "<li><a href='#feedback'>Feedback</a></li>" \
    "</ol><hr />" \
    "<a name='overview' /><h4>Overview</h4>" \
    "<p>PyDiaGUI is a graphical user interface to PyDia, a collection of classes to explore debug symbols from MSDIA in python. " \
    "MSDIA is the Microsoft Debug Interface Access Software Development Kit (DIA SDK) that comes with Visual Studio.</p>" \
    "<ul><li>http://msdn.microsoft.com/en-us/library/x93ctkx8.aspx</li></ul>" \
    "<a name='instructions' /><h4>Instructions</h4>" \
    "<p>Open a file that contains compatible debug symbols, usually a <code>.pdb</code> file, with <code>File &rarr; Open...</code>. " \
    "A tree control will appear at the bottom of the window with the root debug symbol of type <code>SymTagExe</code>. " \
    "A page with the extended information of that symbol will also appear in the center of the window.</p>" \
    "<p>Double-click a debug symbol in the tree to open a page with the extended info of that symbol.</p>" \
    "<p>Expand a debug symbol in the tree to see it's tree children, which appear in the following order:</p>" \
    "<ol>" \
    "<li>attribute symbols</li>" \
    "<li><code>Find children...</code> command</li>" \
    "</ol>" \
    "<p>Double-click the <code>Find children...</code> command to search for child debug symbols. " \
    "If a search hasn't been performed yet, expanding the command does the same. " \
    "Symbols found this way appear as tree children of the command.</p>" \
    "<a name='feedback' /><h4>Feedback</h4>" \
    "<p>Please report any bugs or requests of improvement to:</p>" \
    "<ul><li>https://github.com/flaviojs/pydia</li></ul>" \
    "</body></html>"

    return text


def main():
    app = wx.PySimpleApp()
    try:
        gui = PyDiaGUI()
        app.MainLoop()
        del gui
    finally:
        del app


if __name__ == '__main__':
    main()
