
import Qt 4.7

import 'config.js' as Config
import 'util.js' as Util

BorderImage {
    id: root

    property real progress: 0
    property int duration: 0
    property real mousepos: 0
    signal setProgress(real progress)

    source: 'artwork/progressbar_bg.png'

    Rectangle {
        id: seekTimePreviewBackground

        anchors.fill: seekTimePreview
        color: '#dfffffff'
        opacity: seekTimePreview.opacity
        radius: Config.smallSpacing
    }

    Text {
        id: seekTimePreview
        anchors.bottom: parent.top
        text: Util.formatDuration(root.mousepos*duration)
        font.pixelSize: 50
        horizontalAlignment: Text.AlignHCenter
        color: 'black'
        anchors.left: parent.left
        anchors.leftMargin: parent.width * root.mousepos - width/2
        anchors.bottomMargin: Config.largeSpacing
        opacity: mouseArea.pressed?1:0
        scale: mouseArea.pressed?1:.5
        transformOrigin: Item.Bottom

        Behavior on opacity { PropertyAnimation { } }
        Behavior on scale { PropertyAnimation { } }
    }

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
        id: mouseArea

        anchors.fill: parent
        onClicked: {
            root.setProgress(mouse.x / root.width)
        }
        onPositionChanged: {
            root.mousepos = (mouse.x/root.width)
            if (root.mousepos < 0) root.mousepos = 0
            if (root.mousepos > 1) root.mousepos = 1
        }
        onPressed: {
            root.mousepos = (mouse.x/root.width)
            if (root.mousepos < 0) root.mousepos = 0
            if (root.mousepos > 1) root.mousepos = 1
        }
    }
}

