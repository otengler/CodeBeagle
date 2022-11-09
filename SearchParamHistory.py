from PyQt5.QtCore import Qt, QAbstractItemModel, QSettings, QModelIndex, QStringListModel
import AppConfig

class SearchParamHistory:
    def __init__(self, storageKey: str, maxItems: int = 20):
        self.storageKey = storageKey
        self.itemModel = QStringListModel()
        self.maxItems = maxItems
        self.__restoreItems()

    def model(self) -> QAbstractItemModel:
        return self.itemModel

    def addItem(self, item: str) -> None:
        if not self.itemModel or not item:
            return

        if self.itemModel.insertRow(0):
            firstRow = self.itemModel.index(0, 0)
            self.itemModel.setItemData(firstRow, {Qt.DisplayRole: item})

        storeItems = [item]
        if self.itemModel.rowCount() > 0:    
            toDelete=[]
            for row in range(1, self.itemModel.rowCount()):
                index = self.itemModel.index(row, 0)
                previousItem = self.itemModel.data(index, Qt.DisplayRole)
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
                    self.itemModel.setItemData(self.itemModel.index(row, 0), {Qt.DisplayRole: strList[row]})
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

        history = SearchParamHistory(storageKey, 2)
        self.histories[storageKey] = history
        return history

paramHistory = SearchParamHistoryCollection()
def getSearchParamHistory(storageKey: str):
    return paramHistory.get(storageKey)