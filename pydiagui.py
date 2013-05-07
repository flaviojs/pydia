

import sys, os, traceback
import wx
import wx.py.crust
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


class PyDiaSymbolPanel(wx.Panel):
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

        self.SetSize(wx.Size(800, 600))
        self.SetMinSize(wx.Size(400, 300))
        self.Centre()
        self.Show(True)
        
        # status bar
        self.statusbar = self.CreateStatusBar()

        # tool bar
        ## TODO
        
        #print "menubar"
        self.MakeMenuBar()
        #print "shell"
        self.MakeShellPane()
        #print "symboltree"
        self.MakeSymbolTreePane()
        #print "events"
        self.BindEvents()

        self.mgr.Update()
        self.statusbar.SetStatusText("Ready")
        #print "done"

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
                try:
                    self.statusbar.PushStatusText("Loading {}...".format(path))
                    self.OpenSession(path)
                    self.statusbar.PopStatusText()
                except Exception as e:
                    desc = traceback.format_exc()
                    self.log.write(desc)
                    dlg = wx.MessageDialog(self, 'Failed to load {}\n\n{}'.format(path, desc),
                               'Error:',
                                wx.OK | wx.ICON_ERROR
                                )
                    dlg.ShowModal()
                    dlg.Destroy()
                    break
        dlg.Destroy()
        self.statusbar.SetStatusText("Ready")

    def OnClose(self, evt):
        self.CloseSession()

    def OnAbout(self, evt):
        msg = ["This is a graphical user interface to PyDia, a collection of classes to explore debug symbols from MSDIA in python.\n",
               "MSDIA is the Microsoft Debug Interface Access Software Development Kit that comes with Visual Studio.\n",
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

    def OnExit(self, event):
        """close the frame"""
        self.Close(True)

    def MakeMenuBar(self):
        filemenu = wx.Menu()
        filemenu.Append(wx.ID_OPEN, "&Open...", "Open existing pdb/exe/dll file")
        filemenu.Append(wx.ID_CLOSE, "Close", "Close the active file")
        filemenu.Enable(wx.ID_CLOSE, False)
        filemenu.AppendSeparator()
        filemenu.Append(wx.ID_EXIT, "E&xit", "Terminate the program")

        helpmenu = wx.Menu()
        helpmenu.Append(wx.ID_ABOUT, "&About...", "Display program information")
        
        menubar = wx.MenuBar()
        menubar.Append(filemenu, "&File")
        menubar.Append(helpmenu, "&Help")
        self.SetMenuBar(menubar)

    def MakeShellPane(self):
        return ## TODO figure out why it's hanging the app sometimes during load
        paneinfo = aui.AuiPaneInfo().Name("shell").Caption("Python Shell")
        paneinfo.Center().CloseButton(False).MaximizeButton(True).MinimizeButton(True).Hide()

        intro = 'Welcome To PyCrust %s' % wx.py.version.VERSION
        shell = wx.py.crust.Crust(self, intro = intro)
        #shell = wx.py.shell.Shell(self, intro = intro)
        self.mgr.AddPane(shell, paneinfo)

    def MakeSymbolTreePane(self):
        paneinfo = aui.AuiPaneInfo().Name("symboltree").Caption("Symbol Tree")
        paneinfo.Bottom().CloseButton(False).MaximizeButton(True).MinimizeButton(True).Hide()
        
        imglist = wx.ImageList(16, 16, initialCount = 3)
        imglist.Add(wx.ArtProvider.GetBitmap(wx.ART_EXECUTABLE_FILE, wx.ART_OTHER, wx.Size(16, 16)))
        imglist.Add(wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16, 16)))
        imglist.Add(wx.ArtProvider.GetBitmap(wx.ART_FIND, wx.ART_OTHER, wx.Size(16, 16)))
        self.TREE_ART_ROOT_SYMBOL       = 0 # root symbol, SymTagExe
        self.TREE_ART_ATTRIBUTE_SYMBOL  = 1 # attribute symbol
        self.TREE_ART_CHILD_SYMBOL      = 1 # child symbol
        self.TREE_ART_SEARCH_FILTER     = 2 # search filter

        tree = wx.TreeCtrl(self)
        tree.AssignImageList(imglist)
        self.mgr.AddPane(tree, paneinfo)

    def BindEvents(self):
        wx.EVT_MENU(self, wx.ID_OPEN, self.OnOpen)
        wx.EVT_MENU(self, wx.ID_CLOSE, self.OnClose)
        wx.EVT_MENU(self, wx.ID_EXIT, self.OnExit)
        wx.EVT_MENU(self, wx.ID_ABOUT, self.OnAbout)

    def OpenSession(self, path):
        session = pydia.PyDia(path)
        self.CloseSession()
        self.session = session

        symbol = self.session.globalScope
        symIndexId = symbol.symIndexId

        paneinfo = aui.AuiPaneInfo().Name("symbol_{}".format(symIndexId)).Caption("Symbol #{}".format(symIndexId))
        paneinfo.Center().CloseButton(True).MaximizeButton(True).MinimizeButton(True).Show()
        pane = PyDiaSymbolPanel(self, session, symbol, self.log)
        self.mgr.AddPane(pane, paneinfo)

        tree = self.mgr.GetPane("symboltree").Show().window
        root = tree.AddRoot("{} - {}".format(symIndexId, path), self.TREE_ART_ROOT_SYMBOL)
        tree.SetPyData(root, pane)
        tree.SetItemHasChildren(root, True)

        self.mgr.Update()
        self.GetMenuBar().FindItemById(wx.ID_CLOSE).Enable(True)

    def CloseSession(self):
        del self.session
        self.session = None
        
        tree = self.mgr.GetPane("symboltree").Hide().window

        def removePanes(self, tree, item):
            if not item.IsOk():
                return
            pane = tree.GetPyData(item)
            if pane:
                pane.Hide()
                self.mgr.DetachPane(pane)
                self.RemoveChild(pane)
            item, cookie = tree.GetFirstChild(item)
            while item.IsOk():
                removePanes(self, tree, item)
                item = tree.GetNextChild(item, cookie)
        removePanes(self, tree, tree.GetRootItem())
        tree.DeleteAllItems()
            
        self.mgr.Update()
        self.GetMenuBar().FindItemById(wx.ID_CLOSE).Enable(False)

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
