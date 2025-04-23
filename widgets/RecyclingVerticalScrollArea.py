# -*- coding: utf-8 -*-
"""
Copyright (C) 2013 Oliver Tengler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from typing import Any, List, Iterator, Tuple, Dict, DefaultDict, Optional
from abc import ABC,abstractmethod
import bisect
import collections
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QResizeEvent
from PyQt5.QtWidgets import QLabel, QLayout, QScrollArea, QWidget

def doLinesIntersect (y1: int, length1: int, y2: int, length2: int) -> bool:
    if y1 < y2:
        return  y1+length1 > y2
    else:
        return y2+length2 >  y1

class ScrollAreaItem (ABC):
    def __init__ (self,  height: int) -> None:
        self.height = height
        self.id: int = 0

    @abstractmethod
    def generateItem (self, parent: Optional[QWidget]) -> QWidget:
        pass

    @abstractmethod
    def configureItem(self, item: QWidget) -> None:
        pass

    @abstractmethod
    def getType(self) -> Any:
        pass

class Labeltem (ScrollAreaItem):
    def __init__(self, text: str, bIsBold: bool, height: int) -> None:
        super ().__init__(height)
        self.text = text
        self.bIsBold = bIsBold

    def generateItem (self, parent: Optional[QWidget]) -> QWidget:
        return QLabel("", parent)

    def configureItem(self, item: QWidget) -> None:
        item.setFixedHeight(self.height)
        if self.bIsBold:
            text = "<b>" + self.text + "</b>"
        else:
            text = self.text
        item.setText(text)

    def getType(self) -> Any:
        return QLabel

class SrollAreaItemList:
    def __init__(self,  spacing:int = 7) -> None:
        self.spacing = spacing
        self.clear()

    def clear(self) -> None:
        self.items: List[ScrollAreaItem] = []
        self.yStarts: List[int] = []
        self.y = self.spacing
        self.nextId = 1

    def __len__(self) -> int:
        return len(self.items)

    def addItem (self, item: ScrollAreaItem) -> int:
        """Adds an item to the list and returns its index in the item list."""
        item.id = self.nextId
        self.nextId += 1
        self.items.append(item)
        self.yStarts.append(self.y)
        self.y += (item.height+self.spacing)
        return len(self.items)-1

    def itemYPos (self, index: int) -> int:
        if index>=len(self.yStarts):
            return 0
        return self.yStarts[index]

    def height(self) -> int:
        if not self.items:
            return 0
        last = len(self.items)-1
        return self.yStarts[last]+self.items[last].height+self.spacing

    def visibleItems (self, y: int, height: int) -> Iterator[Tuple[int, ScrollAreaItem]]:
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

    def __indexBeforePos(self,  yPos: int) -> int:
        index = bisect.bisect_left(self.yStarts,  yPos)
        if index > 0:
            index -= 1
        return index

class EmptyLayout(QLayout):
    """
    This layout works around the problem that child wigets of the scrollarea widget are invisible if the scrollarea widget
    has no layout. If this is a bug or as designed - I don't know.
    """
    def itemAt(self, _: int) -> None:
        return None

    def takeAt(self, _: int) -> None:
        return None

    def count(self) -> int:
        return 0

    def sizeHint(self) -> QSize:
        pw = self.parentWidget()
        if pw:
            return pw.size()
        return QSize()

class RecyclingVerticalScrollArea(QScrollArea):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.items: Optional[SrollAreaItemList] = None
        self.activeWidgets: Dict[int, QWidget] = {} # id to widget
        self.reservedWidgets: DefaultDict[str, list[QWidget]] = collections.defaultdict(list) # type name to widgets
        w = QWidget(self)
        w.setLayout(EmptyLayout(w))
        self.setWidget(w)

    def scrollToNthItem (self, index: int) -> None:
        if self.items:
            self.ensureVisible (0, self.items.itemYPos(index),  0,  int(self.height()/2))

    def resizeEvent(self, event: Optional[QResizeEvent]) -> None:
        super().resizeEvent(event)
        self.__refreshItems()

    def scrollContentsBy (self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        self.__refreshItems()

    def setItems (self, items: SrollAreaItemList) -> None:
        self.__reset()
        self.items = items
        widget = self.widget()
        if widget:
            widget.setFixedHeight(self.items.height())
        self.__refreshItems()

    def __reset (self) -> None:
        for w in self.activeWidgets.values():
            w.close()
        self.activeWidgets.clear()
        for wlist in self.reservedWidgets.values():
            for w in wlist:
                w.close()
        self.reservedWidgets.clear()

    def __refreshItems (self) -> None:
        if not self.items:
            return

        scrollBar = self.verticalScrollBar()
        if not scrollBar:
            return
        
        y = scrollBar.value()
        size = self.size()
        width = size.width()
        height = size.height()

        # Iterate all widgets, those which are no longer visible are returned under their class name to
        # the map self.reservedWidgets for future use.
        inactive: List[int] = []
        for ident, w in self.activeWidgets.items():
            wg = w.geometry()
            if  not doLinesIntersect (y, height,  wg.top(),  wg.height()):
                self.reservedWidgets[str(w.__class__)].append(w)
                inactive.append(ident)
        for ident in inactive:
            del self.activeWidgets[ident]

        for itemY,  item in self.items.visibleItems (y, height):
            margin = self.__getScrollViewWidthMargin()
            if not item.id in self.activeWidgets:
                reserve = self.reservedWidgets[item.getType()]
                if reserve:
                    w = reserve.pop()
                else:
                    # No element left, create a new one
                    w = item.generateItem (self.widget())
                    w.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                item.configureItem(w)
                w.move(self.items.spacing, itemY)
                w.setFixedSize(width-margin, item.height)
                w.show()
                self.activeWidgets[item.id] = w
            else:
                self.activeWidgets[item.id].setFixedWidth(width-margin)

    def __getScrollViewWidthMargin (self) -> int:
        # Again not so nice. Without adding 7 pixels the text edit is too close to the scrollbar
        if not self.items:
            return 0

        scrollBar = self.verticalScrollBar()
        if not scrollBar:
            return 0

        width: int = 2 * self.items.spacing+7 + scrollBar.width()
        return width

def main() -> None:
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
