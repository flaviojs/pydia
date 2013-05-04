

import sys, os, traceback, thread
import wx
from wx.lib.scrolledpanel import ScrolledPanel
from pydia import *

ID_ABOUT = wx.NewId()
ID_EXIT  = wx.NewId()
ID_RUNCODE = wx.NewId()

FRAMETB = False
TBFLAGS = ( wx.TB_HORIZONTAL
            | wx.NO_BORDER
            | wx.TB_FLAT
            #| wx.TB_TEXT
            #| wx.TB_HORZ_LAYOUT
            )

assertMode = wx.PYAPP_ASSERT_DIALOG
workThreadLock = threading.RLock() # only one worker at a time

class Log:
    def WriteText(self, text):
        print text
        return
        if text[-1:] == '\n':
            text = text[:-1]
        wx.LogMessage(text)
    write = WriteText

#---------------------------------------------------------------------------


class RedirectStdOutToTextCtrl(object):
    """
    Redirects stdout and appends it to a TextCtrl.
    To be used in the 'with' statement.
    Assumes the worker thread can produce output faster than the GUI can handle.
    """
    def __init__(self, textctrl):
        self.textctrl = textctrl
        self.output = []
        self.lock = threading.Lock()

    def __enter__(self):
        self.old_stdout = sys.stdout
        sys.stdout = self

    def __exit__(self, type, value, traceback):
        sys.stdout = self.old_stdout

    def write(self, s):
        """called in the worker thread"""
        with self.lock:
            if len(self.output) == 0:
                wx.CallAfter(self.updateTextCtrl)
            self.output.append(s)

    def updateTextCtrl(self):
        """called in the GUI thread"""
        with self.lock:
            self.textctrl.AppendText(''.join(self.output))
            del self.output[:]


class PyDiaSymbolPage(wx.Panel):
    """Page of particular DIA symbol"""
    def __init__(self, tree, symIndexId, log):
        wx.Panel.__init__(self, tree, -1)

        self.tree = tree
        self.symIndexId = symIndexId
        self.log = log

        # widgets
        self.meta_label = wx.StaticText(self, -1, "Metadata:")
        self.meta_text = wx.TextCtrl(self, -1, style = wx.TE_MULTILINE | wx.TE_READONLY)
        self.run_label1 = wx.StaticText(self, -1, "Python code:")
        self.run_input = wx.TextCtrl(self, -1, style = wx.TE_MULTILINE)
        self.run_button = wx.Button(self, ID_RUNCODE, "Run code (TODO)")
        self.run_label2 = wx.StaticText(self, -1, "Output:")
        self.run_output = wx.TextCtrl(self, -1, style = wx.TE_AUTO_SCROLL | wx.TE_MULTILINE | wx.TE_READONLY)

        # sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.meta_label)
        sizer.Add(self.meta_text, flag = wx.EXPAND)
        sizer.AddSpacer(10)
        sizer.Add(self.run_label1)
        sizer.Add(self.run_input, flag = wx.EXPAND)
        sizer.Add(self.run_button)
        sizer.Add(self.run_label2)
        sizer.Add(self.run_output, flag = wx.EXPAND)
        self.SetSizer(sizer)

        # events
        self.Bind(wx.EVT_BUTTON, self.OnRunCode, id = ID_RUNCODE)

        self.loadMetadata()

    def pydia(self):
        return self.tree.pydia

    def symbol(self):
        return self.tree.pydia.symbolById(self.symIndexId)

    def loadMetadata(self):
        try:
            pydia = self.pydia()
            assert pydia
            symbol = self.symbol()
            assert symbol
            metadata = SymbolPrinter(pydia).metadata(symbol)
            self.meta_text.AppendText('\n'.join(metadata))
        except:
            self.meta_text.AppendText(traceback.format_exc())

    def OnRunCode(self, evt):
        self.run_output.Clear()
        self.run_button.Enable(False)
        self._run_button_label = self.run_button.GetLabel()
        self.run_button.SetLabel("Running...")
        thread.start_new_thread(self.runScript, (self.run_input.GetValue(),))
        sys.stderr.write('OnRunCode END\n')

    def runScript(self, code):
        """called in a worker thread"""
        exc = None
        with workThreadLock:
            try:
                with RedirectStdOutToTextCtrl(self.run_output):
                    exec(code, globals(), {'self': self})
            except:
                exc = traceback.format_exc()
        wx.CallAfter(self.endScript, exc)

    def endScript(self, exc):
        """called in the GUI thread"""
        if exc:
            self.run_output.AppendText(exc)
        self.run_button.Enable(True)
        self.run_button.SetLabel(self._run_button_label)
        del self._run_button_label


class PyDiaSymbolTree(wx.Treebook):
    """Treebook of DIA symbols"""
    def __init__(self, parent, id, log):
        wx.Treebook.__init__(self, parent, id, style=
                             wx.BK_DEFAULT
                             #wx.BK_TOP
                             #wx.BK_BOTTOM
                             #wx.BK_LEFT
                             #wx.BK_RIGHT
                            )
        self.log = log
        self.pydia = None
        
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)
        self.Bind(wx.EVT_TREEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.Bind(wx.EVT_TREEBOOK_PAGE_CHANGING, self.OnPageChanging)

        # This is a workaround for a sizing bug on Mac...
        wx.FutureCall(100, self.AdjustSize)

    def OnDestroy(self, event):
        self.Unload()
        
    def AdjustSize(self):
        #print self.GetTreeCtrl().GetBestSize()
        self.GetTreeCtrl().InvalidateBestSize()
        self.SendSizeEvent()
        #print self.GetTreeCtrl().GetBestSize()
        

    def makeSymbolPage(self, color):
        p = wx.Panel(self, -1)
        return p

    def OnPageChanged(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        sel = self.GetSelection()
        self.log.write('OnPageChanged,  old:%d, new:%d, sel:%d\n' % (old, new, sel))
        event.Skip()

    def OnPageChanging(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        sel = self.GetSelection()
        self.log.write('OnPageChanging, old:%d, new:%d, sel:%d\n' % (old, new, sel))
        event.Skip()

    def Unload(self):
        self.DeleteAllPages() # XXX we only support 1 for now
        if hasattr(self, 'pydia'):
            del self.pydia
            
    def Load(self, path):
        self.Unload()
        self.pydia = PyDia(path)
        win = PyDiaSymbolPage(self, self.pydia.globalScope.symIndexId, self.log)
        self.AddPage(win, SYMTAG_name(self.pydia.globalScope.symTag))
        


class PyDiaGUI(wx.Frame):
    """DIA symbol viewer"""

    # File extensions for the Open dialog.
    wildcard = "All compatible types (*.pdb;*.exe;*.dll)|*.pdb;*.exe;*.dll|" \
               "Program database (*.pdb)|*.pdb|" \
               "Executable (*.exe)|*.exe|" \
               "Dynamic-link library (*.dll)|*.dll|" \
               "All files (*.*)|*.*"

    def __init__(self, parent = None, id = -1, title = "PyDiaGUI", *args, **kwargs):
        super(PyDiaGUI, self).__init__(parent, id, title, *args, **kwargs)

        self.basetitle = self.GetTitle()
        self.log = Log()
        self.CreateGUI()

        self.Centre()
        self.Show(True)

    def CreateGUI(self):
        self.SetSize((600, 400))
        
        # status bar
        self.CreateStatusBar()

        # menu bar
        #filemenu = wx.Menu()
        #filemenu.Append(ID_ABOUT, "&About", "Information about this program")
        #filemenu.AppendSeparator()
        #filemenu.Append(ID_EXIT, "E&xit", "Terminate the program")
        #menubar = wx.MenuBar()
        #menubar.Append(filemenu, "&File")
        #self.SetMenuBar(menubar)
        #wx.EVT_MENU(self, ID_ABOUT, self.OnAbout)
        #wx.EVT_MENU(self, ID_EXIT, self.OnExit)

        # tool bar
        self.toolbar = self.CreateToolBar()
        topen = self.toolbar.AddLabelTool(wx.ID_OPEN, '', wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR),
                                          shortHelp = "Open file", longHelp = "Open a pdb/exe/dll file and start exploring it's debug symbols.")
        self.toolbar.Realize()

        self.Bind(wx.EVT_TOOL, self.OnOpen, topen)

        self.symboltree = PyDiaSymbolTree(self, wx.ID_ANY, self.log)

    def OnOpen(self,event):
        self.log.write("OnOpen")
        
        # Dialog to open a single file.
        dlg = wx.FileDialog(
            self, message="Choose a file",
            defaultDir=os.getcwd(), 
            defaultFile="",
            wildcard=self.wildcard,
            style=wx.OPEN | wx.CHANGE_DIR #| wx.MULTIPLE 
            )
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            assert len(paths) == 1 # XXX we only support 1 for now

            for path in paths:
                try:
                    self.symboltree.Load(path)
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
        pass

    def OnAbout(self,event):
        """show about information"""
        d = wx.MessageDialog( self, " A sample editor \n in wxPython "
                              ,"About Sample Editor", wx.OK)
        d.ShowModal()
        d.Destroy()

    def OnExit(self,event):
        """close the frame"""
        self.Close(True)


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
