
import Qt 4.7

ScaledImage {
    id: nowPlayingThrobber
    signal clicked

    source: 'artwork/nowplaying-tab.png'

    ScaledImage {
        anchors {
            verticalCenter: parent.verticalCenter
            right: parent.right
            rightMargin: (parent.width * .8 - width) / 2
        }
        source: 'icons/nowplaying.png'
    }

    MouseArea {
        anchors.fill: parent
        onPressed: nowPlayingThrobber.clicked()
    }
}
