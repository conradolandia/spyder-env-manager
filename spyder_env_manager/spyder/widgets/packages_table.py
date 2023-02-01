# -*- coding: utf-8 -*-
#
# ----------------------------------------------------------------------------
# Copyright © 2022, Spyder Development Team and spyder-env-manager contributors
#
# Licensed under the terms of the MIT license
# ----------------------------------------------------------------------------

"""
Package table widget.

This is the main widget used in the Spyder env Manager plugin
"""

# Third library imports
from qtpy.compat import to_qvariant
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QAbstractItemView, QMenu, QTableView

# Spyder and local imports
from spyder.api.translations import get_translation
from spyder.config.fonts import DEFAULT_SMALL_DELTA
from spyder.config.gui import get_font
from spyder.utils.palette import SpyderPalette
from spyder.utils.qthelpers import add_actions, create_action

# Localization
_ = get_translation("spyder")


# Column constants
NAME, DESCRIPTION, VERSION = [0, 1, 2]


class EnvironmentPackagesActions:
    # Triggers
    UpdatePackage = "update_package"
    UninstallPackage = "unistall_package"
    InstallPackageVersion = "install_package_version"


class EnvironmentPackagesModel(QAbstractTableModel):
    def __init__(self, parent, text_color=None, text_color_highlight=None):
        QAbstractTableModel.__init__(self)
        self._parent = parent
        self.all_packages = []
        self.packages = []
        self.packages_map = {}

    def flags(self, index):
        """Qt Override."""
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index))

    def data(self, index, role=Qt.DisplayRole):
        """Qt Override."""
        row = index.row()
        if not index.isValid() or not (0 <= row < len(self.packages)):
            return to_qvariant()

        package = self.packages[row]
        column = index.column()

        if role == Qt.DisplayRole:
            if column == NAME:
                text = package["name"]
                return to_qvariant(text)
            elif column == DESCRIPTION:
                text = package["description"]
                return to_qvariant(text)
            elif column == VERSION:
                text = package["version"]
                return to_qvariant(text)
        elif role == Qt.TextAlignmentRole:
            return to_qvariant(int(Qt.AlignCenter))
        elif role == Qt.FontRole:
            return to_qvariant(get_font(font_size_delta=DEFAULT_SMALL_DELTA))
        elif role == Qt.BackgroundColorRole:
            if package["requested"]:
                return to_qvariant(QColor(SpyderPalette.COLOR_OCCURRENCE_4))
        return to_qvariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Qt Override."""
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return to_qvariant(int(Qt.AlignHCenter | Qt.AlignVCenter))
            return to_qvariant(int(Qt.AlignRight | Qt.AlignVCenter))
        if role != Qt.DisplayRole:
            return to_qvariant()
        if orientation == Qt.Horizontal:
            if section == NAME:
                return to_qvariant(_("Name"))
            elif section == DESCRIPTION:
                return to_qvariant(_("Description"))
            elif section == VERSION:
                return to_qvariant(_("Version"))
        return to_qvariant()

    def rowCount(self, index=QModelIndex()):
        """Qt Override."""
        return len(self.packages)

    def columnCount(self, index=QModelIndex()):
        """Qt Override."""
        return 3

    def row(self, row_num):
        """Get row based on model index. Needed for the custom proxy model."""
        return self.packages[row_num]

    def reset(self):
        """Reset model to take into account new search letters."""
        self.beginResetModel()
        self.endResetModel()


class EnvironmentPackagesTable(QTableView):

    sig_action_context_menu = Signal(str, dict)

    def __init__(self, parent, text_color=None):
        QTableView.__init__(self, parent)
        # Setup table model
        self.source_model = EnvironmentPackagesModel(self, text_color=text_color)
        self.setModel(self.source_model)

        # Setup table
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.verticalHeader().hide()
        self.load_packages(False)

    def selection(self, action, package_info):
        """Update selected row."""
        self.sig_action_context_menu.emit(action, package_info)

    def adjust_cells(self):
        """Adjust column size based on contents."""
        fm = self.horizontalHeader().fontMetrics()
        names = [fm.width(p["name"]) for p in self.source_model.packages]
        if names:
            self.setColumnWidth(NAME, max(names))
        descriptions = [fm.width(p["description"]) for p in self.source_model.packages]
        if descriptions:
            self.setColumnWidth(DESCRIPTION, max(descriptions))
        self.horizontalHeader().setStretchLastSection(True)

    def get_package_info(self, index):
        return self.source_model.packages[index]

    def load_packages(self, only_requested=False, packages=None):
        #     packages = [
        #         {
        #             "name": "package name",
        #             "description": "package description",
        #             "version": "0.0.1",
        #             "requested": False,
        #         },
        #     ]
        if packages:
            self.source_model.all_packages = packages
        if not packages and self.source_model.all_packages:
            packages = self.source_model.all_packages
        if packages:
            if only_requested:
                packages = list(filter(lambda package: package["requested"], packages))
            for idx, package in enumerate(packages):
                package["index"] = idx
            packages_map = {package["name"]: package for package in packages}

            self.source_model.packages = packages
            self.source_model.packages_map = packages_map
            self.source_model.reset()
            self.adjust_cells()
            self.sortByColumn(NAME, Qt.AscendingOrder)

    def next_row(self):
        """Move to next row from currently selected row."""
        row = self.currentIndex().row()
        rows = self.source_model.rowCount()
        if row + 1 == rows:
            row = -1
        self.selectRow(row + 1)

    def previous_row(self):
        """Move to previous row from currently selected row."""
        row = self.currentIndex().row()
        rows = self.source_model.rowCount()
        if row == 0:
            row = rows
        self.selectRow(row - 1)

    def contextMenuEvent(self, event):
        """Setup context menu"""
        row = self.rowAt(event.pos().y())
        packages = self.source_model.packages
        if packages and packages[row]["requested"]:
            update_action = create_action(
                self,
                _("Update package"),
                triggered=lambda: self.selection(
                    EnvironmentPackagesActions.UpdatePackage, packages[row]
                ),
            )
            uninstall_action = create_action(
                self,
                _("Uninstall package"),
                triggered=lambda: self.selection(
                    EnvironmentPackagesActions.UninstallPackage, packages[row]
                ),
            )
            change_action = create_action(
                self,
                _("Change package version with a constraint"),
                triggered=lambda: self.selection(
                    EnvironmentPackagesActions.InstallPackageVersion, packages[row]
                ),
            )
            menu = QMenu(self)
            menu_actions = [
                update_action,
                uninstall_action,
                change_action,
            ]
            add_actions(menu, menu_actions)
            menu.setMinimumWidth(100)
            menu.popup(event.globalPos())
            event.accept()

    def focusInEvent(self, e):
        """Qt Override."""
        super(EnvironmentPackagesTable, self).focusInEvent(e)
        self.selectRow(self.currentIndex().row())

    def keyPressEvent(self, event):
        """Qt Override."""
        key = event.key()
        if key in [Qt.Key_Enter, Qt.Key_Return]:
            self.show_editor()
        elif key in [Qt.Key_Backtab]:
            self.parent().reset_btn.setFocus()
        elif key in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            super(EnvironmentPackagesTable, self).keyPressEvent(event)
        else:
            super(EnvironmentPackagesTable, self).keyPressEvent(event)
