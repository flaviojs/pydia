PyDia
=====

PyDia is a collection of classes to explore debug symbols from MSDIA in python.
MSDIA is the [Microsoft Debug Interface Access SDK](http://msdn.microsoft.com/en-us/library/x93ctkx8.aspx) that comes with Visual Studio.

It's incomplete, in the middle of the 3rd iteration.
I shifted focus to a GUI that allowed me to explore around the data
since a `.pdb` or `.exe` can have incorrect debug data.
(when unsure, I need to confirm by checking related data)

_Flávio J. Saraiva_

PyDiaGUI
========

PyDiaGUI is a graphical user interface to PyDia.

Requires [wxPython](http://www.wxpython.org/).
