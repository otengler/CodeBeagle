from typing import Optional, Dict, Any, cast
from PyQt5.QtCore import Qt, QAbstractItemModel, QAbstractListModel, QSettings, QModelIndex, QVariant
import AppConfig
   
# This is like QStringListModel with the only exception that setData does not raise signals.
# This caused combox boxes to change selection.
class MyStringListModel(QAbstractListModel):
    def __init__(self, parent: Optional[QAbstractItemModel] = None) -> None:
        super().__init__(parent)
        self._data: list[str] = []  # list of strings

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0  # No children for any row (flat list)
        return len(self._data)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return QVariant()
        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return self._data[index.row()]
        return QVariant()

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return cast(Qt.ItemFlags, Qt.ItemFlag.NoItemFlags)
        return cast(Qt.ItemFlags, Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

    def removeRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        if row < 0:
            return False
        self._data = self._data[0:row] + self._data[row+count:]
        return True

    def insertRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        if row < 0:
            return False
        self._data = self._data[0:row] + [""] * count + self._data[row:]
        return True

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.DisplayRole) -> bool:
        if index.isValid() and role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            self._data[index.row()] = value
            # Normally we should now raise "dataChanged". But we explicitly do not do this because it changes the selected item
            # for combo boxes on other tabs.
            # self.dataChanged.emit(index, index, [Qt.DisplayRole])
            return True
        return False

class SearchParamHistory:
    def __init__(self, storageKey: str, maxItems: int = 20):
        self.storageKey = storageKey
        self.itemModel = MyStringListModel()
        self.maxItems = maxItems
        self.__restoreItems()

    def model(self) -> QAbstractItemModel:
        return self.itemModel

    def addItem(self, item: str) -> None:
        if not self.itemModel or not item:
            return

        if self.itemModel.insertRow(0):
            firstRow = self.itemModel.index(0, 0)
            self.itemModel.setItemData(firstRow, {Qt.ItemDataRole.DisplayRole: item})

        storeItems = [item]
        if self.itemModel.rowCount() > 0:    
            toDelete=[]
            for row in range(1, self.itemModel.rowCount()):
                index = self.itemModel.index(row, 0)
                previousItem = self.itemModel.data(index, Qt.ItemDataRole.DisplayRole)
                if item == previousItem:
                    toDelete.append(row)
                else:
                    if len(storeItems) < self.maxItems:
                        storeItems.append(previousItem)

            for deleteRow in sorted(toDelete, reverse=True):
                self.itemModel.removeRow(deleteRow)

            # Keep all parameters in the model for one run but only persist up to maxItems. This was neccessary because
            # combo box seems to remember the select index and if the model changes the same index is used which then
            # points to a different entry.
            #while self.itemModel.rowCount() > self.maxItems:
                #self.itemModel.removeRow(self.maxItems)

        settings = QSettings(AppConfig.appCompany, AppConfig.appName)
        settings.setValue(self.storageKey, storeItems)

    def __restoreItems(self) -> None:
        settings = QSettings(AppConfig.appCompany, AppConfig.appName)
        if settings.value(self.storageKey):
            strList = settings.value(self.storageKey)[0:20]
            self.itemModel.beginInsertRows(QModelIndex(), 0, len(strList)-1)
            if self.itemModel.insertRows(0, len(strList)):
                for row in range(len(strList)):
                    self.itemModel.setItemData(self.itemModel.index(row, 0), {Qt.ItemDataRole.DisplayRole: strList[row]})
            self.itemModel.endInsertRows()
        else:
            # Clear model
            rowCount = self.itemModel.rowCount()
            if rowCount > 0:
                self.itemModel.beginRemoveRows(QModelIndex(), 0, rowCount-1)
                for row in range(rowCount-1, -1, -1):
                    self.itemModel.removeRow(row)
                self.itemModel.endRemoveRows()

class SearchParamHistoryCollection:
    def __init__(self) -> None:
        self.histories: Dict[str, SearchParamHistory] = {}

    def get(self, storageKey: str) -> SearchParamHistory:
        if storageKey in self.histories:
            return self.histories[storageKey]

        history = SearchParamHistory(storageKey)
        self.histories[storageKey] = history
        return history

paramHistory = SearchParamHistoryCollection()
def getSearchParamHistory(storageKey: str) -> SearchParamHistory:
    return paramHistory.get(storageKey)