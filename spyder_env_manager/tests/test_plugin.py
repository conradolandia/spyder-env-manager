# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2022, Spyder Development Team and spyder-env-manager contributors
#
# Licensed under the terms of the MIT license
# ----------------------------------------------------------------------------
"""
Spyder Env Manager plugin tests.
"""
# Standard library imports
from unittest.mock import Mock, patch

# Third-party imports
import pytest
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QMainWindow

# Spyder imports
from spyder.api.plugins import Plugins
from spyder.config.manager import CONF

# Local imports
from spyder_env_manager.spyder.plugin import SpyderEnvManager
from spyder_env_manager.spyder.widgets.main_widget import SpyderEnvManagerWidget
from spyder_env_manager.spyder.widgets.helper_widgets import CustomParametersDialog

# Constants
OPERATION_TIMEOUT = 100000


# ---- Fixtures
# ------------------------------------------------------------------------
class MainMock(QMainWindow):
    def __init__(self):
        super().__init__()
        self.switcher = Mock()
        self.main = self
        self.resize(640, 480)

    def get_plugin(self, plugin_name, error=True):
        return Mock()


@pytest.fixture
def spyder_env_manager(tmp_path, qtbot, monkeypatch):
    backends_root_path = tmp_path / "backends"
    backends_root_path.mkdir(parents=True)
    window = MainMock()

    def get_conf(self, option, default=None, section=None):
        if option == "environments_path":
            return str(backends_root_path)
        else:
            return default

    monkeypatch.setattr(SpyderEnvManagerWidget, "get_conf", get_conf)

    plugin = SpyderEnvManager(parent=window, configuration=CONF)
    widget = plugin.get_widget()
    window.setCentralWidget(widget)
    qtbot.addWidget(window)
    window.show()

    yield widget

    qtbot.waitUntil(lambda: widget.actions_enabled, timeout=OPERATION_TIMEOUT)
    widget.close()


def test_spyder_env_manager(spyder_env_manager, qtbot):
    """Setup plugin widget, show it and create an environment."""
    assert (
        spyder_env_manager.select_environment.currentText()
        == "No environments available"
    )
    assert (
        spyder_env_manager.stack_layout.currentWidget() == spyder_env_manager.infowidget
    )

    def handle_env_creation_dialog():
        dialog = spyder_env_manager.findChild(CustomParametersDialog)
        dialog.lineedit_string.setText("test_env")
        dialog.combobox_edit.setCurrentText("3.9")
        dialog.accept()

    QTimer.singleShot(100, handle_env_creation_dialog)
    spyder_env_manager._message_new_environment()

    qtbot.waitUntil(
        lambda: spyder_env_manager.stack_layout.currentWidget()
        == spyder_env_manager.packages_table,
        timeout=OPERATION_TIMEOUT,
    )
    assert spyder_env_manager.select_environment.currentText() == "test_env"
    assert spyder_env_manager.packages_table.source_model.rowCount() == 2
