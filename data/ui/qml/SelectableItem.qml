
import Qt 4.7

import 'config.js' as Config

Item {
    id: selectableItem
    signal selected(variant item)
    signal contextMenu(variant item)

    /* The width of the area from the left edge that when
     * pressed will signal contextMenu instead of selected.
     */
    property int singlePressContextMenuLeftBorder: 0

    height: Config.listItemHeight
    width: parent.width

    Rectangle {
        id: highlight
        property real maxOpacity: .2

        opacity: mouseArea.pressed?maxOpacity:0
        color: "white"
        anchors {
            left: parent.left
            right: parent.right
            verticalCenter: parent.verticalCenter
        }
        height: parent.height + parent.height * (opacity - maxOpacity)

        Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
    }

    MouseArea {
        id: mouseArea
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        anchors.fill: parent
        onClicked: {
            if (mouse.x <= selectableItem.singlePressContextMenuLeftBorder) {
                selectableItem.contextMenu(modelData)
            } else if (mouse.button == Qt.LeftButton) {
                selectableItem.selected(modelData)
            } else if (mouse.button == Qt.RightButton) {
                selectableItem.contextMenu(modelData)
            }
        }
        onPressAndHold: selectableItem.contextMenu(modelData)
    }
}

