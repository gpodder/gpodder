
import QtQuick 1.1
import com.nokia.meego 1.0

Item {
    id: actionmenu

    /* ListView for which this menu is valid */
    property variant listview

    /* Collect actions from the menu here */
    default property alias content: actions.children
    Item { id: actions }

    /* Show action menu when this function is called */
    function open() {
        contextMenu.open();
    }

    anchors.fill: parent

    ContextMenu {
        id: contextMenu

        MenuLayout {
            id: menuLayout

            Repeater {
                model: actions.children

                MenuItem {
                    text: modelData.text
                    onClicked: modelData.clicked()
                }
            }
        }
    }
}

