
from PySide.QtCore import QObject, Slot, Signal


class CommonController(QObject):

    deleteMe = Signal(QObject)

    def __init__(self, parent):
        QObject.__init__(self, parent)

        self._view = None

    @property
    def view(self):
        return self._view

    @view.setter
    def view(self, value):
        self._view = value
        self._view.object.myController = self

    @Slot()
    def close(self):
        self._view.object.visible = False
        del self._view
        self.deleteMe.emit(self)

    def registerProperties(self, context):
        pass
