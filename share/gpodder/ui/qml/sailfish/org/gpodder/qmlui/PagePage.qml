
import QtQuick 1.1
import Sailfish.Silica 1.0

Page {
    id: pagePage
    signal closed
    property bool hasMenu: actions.length > 0
    property bool lockToPortrait: false
    property alias actions: actionMenu.content
    property alias listview: actionMenu.listview

    allowedOrientations: lockToPortrait?Orientation.Portrait:Orientation.All

    function close() {
        pageStack.pop();
        closed();
    }

    ActionMenu {
        id: actionMenu
    }
}

