from PyQt5.QtCore import Qt, QAbstractItemModel, QAbstractListModel, QSettings, QModelIndex, QVariant
import AppConfig
   
# This is like QStringListModel with the only exception that setData does not raise signals.
# This caused combox boxes to change selection.
class MyStringListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []  # list of strings

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0  # No children for any row (flat list)
        return len(self._data)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        if role in [Qt.DisplayRole, Qt.EditRole]:
            return self._data[index.row()]
        return QVariant()

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

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

    def setData(self, index, value, role=Qt.DisplayRole):
        if index.isValid() and role in [Qt.DisplayRole, Qt.EditRole]:
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
    def __init__(self):
        self.histories = {}

    def get(self, storageKey: str) -> SearchParamHistory:
        if storageKey in self.histories:
            return self.histories[storageKey]

        history = SearchParamHistory(storageKey)
        self.histories[storageKey] = history
        return history

paramHistory = SearchParamHistoryCollection()
def getSearchParamHistory(storageKey: str):
    return paramHistory.get(storageKey)