
import QtQuick 1.1
import com.nokia.meego 1.0

Page {
    id: pagePage
    signal closed
    property bool hasMenu: actions.length > 0
    property alias actions: actionMenu.content

    function close() {
        pageStack.pop();
        closed();
    }

    tools: ToolBarLayout {
        ToolIcon {
            visible: pageStack.depth > 1
            anchors.left: parent.left
            iconId: "icon-m-toolbar-back-white"
            onClicked: pagePage.close();
        }

        ToolIcon {
            visible: pagePage.hasMenu
            onClicked: actionMenu.open();
            anchors.right: parent.right
            iconId: "toolbar-view-menu"
        }
    }

    ActionMenu {
        id: actionMenu
    }
}

