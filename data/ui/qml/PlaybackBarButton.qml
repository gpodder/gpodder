
import Qt 4.7

import 'config.js' as Config

Image {
    signal clicked()

    width: 64 * Config.scale
    height: 64 * Config.scale

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        onClicked: parent.clicked()
    }

    Rectangle {
        anchors.fill: parent
        color: 'black'
        radius: Config.smallSpacing
        opacity: mouseArea.pressed?.2:0
    }
}

