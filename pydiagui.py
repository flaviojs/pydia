

import sys, os, traceback
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


class SymbolPanel(wx.Panel):
    def __init__(self, parent, session, symbol, log):
        wx.Panel.__init__(self, parent)

        assert session
        assert symbol
        self.log = Log()
        self.symIndexId = symbol.symIndexId
        
        self.label = wx.StaticText(self, -1, label = "Metadata:")
        metadata = pydia.SymbolPrinter(session).metadata(symbol)
        self.text = wx.TextCtrl(self, -1, value = '\n'.join(metadata), style = wx.TE_MULTILINE | wx.TE_READONLY)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.label, 0)
        sizer.Add(self.text, 0, wx.EXPAND)
        self.SetSizer(sizer)


class SymbolData(object):
    def __init__(self, session, symbol):
        assert session
        assert symbol
        self.session = session
        self.symbol = symbol

    def __del__(self):
        del self.symbol
        del self.session


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
            #print "menubar"
            self.MakeMenuBar()
            #print "toolbar"
            self.MakeToolBar()
            #print "shell"
            self.MakeShellPane()
            #print "symboltree"
            self.MakeSymbolTreePane()
            #print "symbolbook"
            self.MakeSymbolBook()
            #print "events"
            self.BindEvents()

            self.AddWelcomePage()
            self.statusbar.SetStatusText("Ready")
            self.DoUpdate()
            #print "done"
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
        if item and item.IsOk() and tree.ItemHasChildren(item) and tree.GetChildrenCount(item, False) == 0:
            # attribute symbols
            data = tree.GetPyData(item)
            for attr in pydia.SymbolPrinter(data.session).attributes(data.symbol):
                try:
                    symbol = getattr(data.symbol, attr)
                    if symbol and type(symbol) == type(data.symbol):
                        title = "{} - {} = {} {}".format(
                            symbol.symIndexId, attr,
                            pydia.SYMTAG_name(symbol.symTag), symbol.name)
                        image = self.TREE_ART_ATTRIBUTE_SYMBOL
                        data = SymbolData(data.session, symbol)
                        child = tree.AppendItem(item, title, image)
                        tree.SetPyData(child, data)
                        tree.SetItemHasChildren(child, True)
                except:
                    pass
            # search filter
            title = "Find children..."
            image = self.TREE_ART_SEARCH_FILTER
            tree.AppendItem(item, title, image)
            #print "OnTreeItemExpanding: children added"

    def OnTreeItemActivate(self, event):
        tree = self.mgr.GetPane("symboltree").window
        item = event.GetItem()
        if item and item.IsOk():
            image = tree.GetItemImage(item)
            data = tree.GetPyData(item)
            if image == self.TREE_ART_SEARCH_FILTER:
                # search for children
                print "TODO search filter"
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
        title = "{} - {}".format(symbol.symIndexId, path)
        image = self.TREE_ART_ROOT_SYMBOL
        data = SymbolData(session, symbol)
        root = tree.AddRoot(title, image)
        tree.SetPyData(root, data)
        tree.SetItemHasChildren(root, True)

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


def GetIntroText():
    text = \
    "<html><body>" \
    "<h3>Welcome to PyDiaGUI</h3>" \
    "<p>PyDiaGUI is a graphical user interface to PyDia, a collection of classes to explore debug symbols from MSDIA in python.<p>" \
    "<p>MSDIA is the Microsoft Debug Interface Access Software Development Kit (DIA SDK) that comes with Visual Studio.<p>" \
    "<ul><li>http://msdn.microsoft.com/en-us/library/x93ctkx8.aspx</li></ul>" \
    "<p>Please report any bugs or requests of improvements to:<p>" \
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
