
import QtQuick 1.1

import 'config.js' as Config

Item {
    id: selectableItem
    signal selected(variant item)
    signal contextMenu(variant item)

    property bool pressed: mouseArea.pressed
    property bool inSelection: false

    height: Config.listItemHeight
    width: parent.width

    Rectangle {
        id: selectionHighlight

        anchors.fill: parent
        visible: selectableItem.inSelection
        color: Config.selectColorBg
        opacity: .5
    }

    MouseArea {
        id: mouseArea

        anchors.fill: parent
        onClicked: parent.selected(modelData)
        onPressAndHold: parent.contextMenu(modelData)
    }
}

