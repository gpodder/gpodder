
import Qt 4.7

ScaledImage {
    id: nowPlayingThrobber
    property bool opened
    signal clicked

    source: 'artwork/nowplaying-tab.png'

    ScaledImage {
        anchors {
            verticalCenter: parent.verticalCenter
            right: parent.right
            rightMargin: (parent.width * .8 - width) / 2
        }
        rotation: (parent.opened)?-90:0
        source: (parent.opened)?'icons/back_inv.png':'icons/nowplaying.png'

        Behavior on rotation { NumberAnimation { duration: 100 } }
    }

    MouseArea {
        anchors.fill: parent
        onPressed: nowPlayingThrobber.clicked()
    }
}
