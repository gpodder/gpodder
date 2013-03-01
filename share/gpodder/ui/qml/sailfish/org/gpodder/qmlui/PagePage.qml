
import QtQuick 1.1
import Sailfish.Silica 1.0

Page {
    id: pagePage
    signal closed
    property bool hasMenu: actions.length > 0
    property alias actions: actionMenu.content
    property alias listview: actionMenu.listview

    function close() {
        pageStack.pop();
        closed();
    }

    ActionMenu {
        id: actionMenu
    }
}

