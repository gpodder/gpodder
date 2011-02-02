
import Qt 4.7

Image {
    id: nowPlayingThrobber
    signal clicked

    source: 'artwork/nowplaying.png'

    MouseArea {
        anchors.fill: parent
        onClicked: nowPlayingThrobber.clicked()
    }
}
