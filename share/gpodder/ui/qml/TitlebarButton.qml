
import QtQuick 1.1

import 'config.js' as Config

Item {
    id: titlebarButton
    signal clicked
    property alias source: icon.source
    property alias rotation: icon.rotation

    anchors.top: parent.top
    anchors.bottom: parent.bottom

    width: Config.switcherWidth

    Rectangle {
        anchors.fill: parent
        color: 'white'
        opacity: mouseArea.pressed?.3:0

        Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
    }

    ScaledIcon {
        id: icon
        anchors {
            verticalCenter: parent.verticalCenter
            right: parent.right
            rightMargin: (parent.width * .8 - width) / 2
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        onClicked: titlebarButton.clicked()
    }

}
