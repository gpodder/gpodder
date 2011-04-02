
import Qt 4.7

BorderImage {
    id: root

    property real progress: 0
    signal setProgress(real progress)

    source: 'artwork/progressbar_bg.png'

    border {
        top: 18
        left: 18
        right: 18
        bottom: 18
    }

    Item {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: parent.width * root.progress
        clip: true

        BorderImage {
            width: root.width
            source: 'artwork/progressbar_fg.png'
            border {
                top: 18
                left: 18
                right: 18
                bottom: 18
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: {
            root.setProgress(mouse.x / root.width)
        }
    }
}

