
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

        Behavior on opacity { NumberAnimation { duration: 200 } }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        onClicked: selectableItem.selected(modelData)
        onPressAndHold: selectableItem.contextMenu(modelData)
    }
}

