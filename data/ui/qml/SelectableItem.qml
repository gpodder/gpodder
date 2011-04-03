
import Qt 4.7

import 'config.js' as Config

Item {
    id: selectableItem
    signal selected(variant item)
    signal contextMenu(variant item)

    height: Config.listItemHeight
    width: parent.width

    Rectangle {
        id: highlight
        opacity: mouseArea.pressed?.2:0
        color: "white"
        anchors.fill: parent

        Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
    }

    MouseArea {
        id: mouseArea
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        anchors.fill: parent
        onClicked: {
            if (mouse.button == Qt.LeftButton) {
                selectableItem.selected(modelData)
            } else if (mouse.button == Qt.RightButton) {
                selectableItem.contextMenu(modelData)
            }
        }
        onPressAndHold: selectableItem.contextMenu(modelData)
    }
}

