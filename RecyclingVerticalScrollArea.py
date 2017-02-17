# -*- coding: utf-8 -*-
"""
Copyright (C) 2013 Oliver Tengler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import abc
import bisect
import collections
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QLayout, QScrollArea, QWidget

def doLinesIntersect (y1, length1, y2, length2):
    if y1 < y2:
        return  y1+length1 > y2
    else:
        return y2+length2 >  y1

class ScrollAreaItem (metaclass = abc.ABCMeta):
    def __init__ (self,  height):
        self.height = height

    @abc.abstractmethod
    def generateItem (self, parent):
        pass

    @abc.abstractmethod
    def configureItem(self, item):
        pass

    @abc.abstractmethod
    def getType(self):
        pass

class Labeltem (ScrollAreaItem):
    def __init__(self, text, bIsBold, height):
        super (Labeltem,  self).__init__( height)
        self.text = text
        self.bIsBold = bIsBold
        self.id = None

    def generateItem (self, parent):
        return QLabel("", parent)

    def configureItem(self, label):
        label.setFixedHeight(self.height)
        if self.bIsBold:
            text = "<b>" + self.text + "</b>"
        else:
            text = self.text
        label.setText(text)

    def getType(self):
        return QLabel

class SrollAreaItemList:
    def __init__(self,  spacing = 7):
        self.spacing = spacing
        self.clear()

    def clear(self):
        self.items = []
        self.yStarts = []
        self.y = self.spacing
        self.nextId = 1

    def __len__(self):
        return len(self.items)

    def addItem (self, item):
        """Adds an item to the list and returns its index in the item list."""
        item.id = self.nextId
        self.nextId += 1
        self.items.append(item)
        self.yStarts.append(self.y)
        self.y += (item.height+self.spacing)
        return len(self.items)-1

    def itemYPos (self, index):
        if index>=len(self.yStarts):
            return 0
        return self.yStarts[index]

    def height(self):
        if not self.items:
            return 0
        last = len(self.items)-1
        return self.yStarts[last]+self.items[last].height+self.spacing

    def visibleItems (self, y, height):
        index = self.__indexBeforePos (y)

        while index<len(self.items):
            item = self.items[index]
            itemY = self.yStarts[index]
            if doLinesIntersect(y, height, itemY,  item.height):
                yield itemY, item
            else:
                if itemY > y+height:
                    break
            index += 1

    def __indexBeforePos(self,  yPos):
        index = bisect.bisect_left(self.yStarts,  yPos)
        if index > 0:
            index -= 1
        return index

class EmptyLayout(QLayout):
    """
    This layout works around the problem that child wigets of the scrollarea widget are invisible if the scrollarea widget
    has no layout. If this is a bug or as designed - I don't know.
    """
    def __init__(self,  parent):
        super(EmptyLayout, self).__init__(parent)

    def itemAt(self, index):
        return None

    def takeAt(self, index):
        return None

    def count(self):
        return 0

    def sizeHint(self):
        return self.parent().size()

class RecyclingVerticalScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super(RecyclingVerticalScrollArea, self).__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.items = None
        self.activeWidgets = {} # id to widget
        self.reservedWidgets = collections.defaultdict(list) # type name to widgets
        w = QWidget(self)
        w.setLayout(EmptyLayout(w))
        self.setWidget(w)

    def scrollToNthItem (self, index):
        if self.items:
            self.ensureVisible (0, self.items.itemYPos(index),  0,  int(self.height()/2))

    def resizeEvent(self, event):
        super(RecyclingVerticalScrollArea, self).resizeEvent(event)
        self.__refreshItems()

    def scrollContentsBy (self,  dx, dy):
        super(RecyclingVerticalScrollArea, self).scrollContentsBy(dx, dy)
        self.__refreshItems()

    def setItems (self,  items):
        self.__reset()
        self.items = items
        self.widget().setFixedHeight(self.items.height())
        self.__refreshItems()

    def __reset (self):
        for w in self.activeWidgets.values():
            w.close()
        self.activeWidgets.clear()
        for wlist in self.reservedWidgets.values():
            for w in wlist:
                w.close()
        self.reservedWidgets.clear()

    def __refreshItems (self):
        if not self.items:
            return

        y = self.verticalScrollBar().value()
        size = self.size()
        width = size.width()
        height = size.height()

        # Iterate all widgets, those which are no longer visible are returned under their class name to
        # the map self.reservedWidgets for future use.
        inactive = []
        for id, w in self.activeWidgets.items():
            wg = w.geometry()
            if  not doLinesIntersect (y, height,  wg.top(),  wg.height()):
                self.reservedWidgets[w.__class__].append(w)
                inactive.append(id)
        for id in inactive:
            del self.activeWidgets[id]

        for itemY,  item in self.items.visibleItems (y, height):
            margin = self.__getScrollViewWidthMargin()
            if not item.id in self.activeWidgets:
                reserve = self.reservedWidgets[item.getType()]
                if reserve:
                    w = reserve.pop()
                else:
                    # No element left, create a new one
                    w = item.generateItem (self.widget())
                    w.setAttribute(Qt.WA_DeleteOnClose)
                item.configureItem(w)
                w.move(self.items.spacing, itemY)
                w.setFixedSize(width-margin, item.height)
                w.show()
                self.activeWidgets[item.id] = w
            else:
                self.activeWidgets[item.id].setFixedWidth(width-margin)

    def __getScrollViewWidthMargin (self):
        # Again not so nice. Without adding 7 pixels the text edit is too close to the scrollbar
        width = 2*self.items.spacing+7+self.verticalScrollBar().width()
        return width

def main():
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)

    items = SrollAreaItemList()
    for i in range(1000):
        labelItem = Labeltem("%u" % (i+1, ),  False,  14)
        items.addItem(labelItem)

    w = RecyclingVerticalScrollArea(None)
    w.setItems(items)

    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
