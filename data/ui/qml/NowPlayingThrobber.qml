
import Qt 4.7

import 'config.js' as Config

Image {
    id: nowPlayingThrobber
    property bool opened
    signal clicked

    source: 'artwork/nowplaying-tab.png'

    height: Config.headerHeight
    width: Config.switcherWidth

    ScaledIcon {
        anchors {
            verticalCenter: parent.verticalCenter
            right: parent.right
            rightMargin: (parent.width * .8 - width) / 2
        }
        rotation: (parent.opened)?-90:0
        source: (parent.opened)?'icons/back_inv.png':'icons/play_inv.png'

        Behavior on rotation { NumberAnimation { duration: 100 } }
    }

    MouseArea {
        anchors.fill: parent
        onPressed: nowPlayingThrobber.clicked()
    }
}

