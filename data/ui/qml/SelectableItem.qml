
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
            if (mouse.button == Qt.LeftButton) {
                selectableItem.selected(modelData)
            } else if (mouse.button == Qt.RightButton) {
                selectableItem.contextMenu(modelData)
            }
        }
        onPressAndHold: selectableItem.contextMenu(modelData)
    }
}

