
import Qt 4.7

import 'config.js' as Config
import 'util.js' as Util

BorderImage {
    id: root

    property real progress: 0
    property int duration: 0
    property real mousepos: 0
    signal setProgress(real progress)

    height: 64 * Config.scale

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
        font.pixelSize: 50 * Config.scale
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
        top: 18 * Config.scale
        left: 18 * Config.scale
        right: 18 * Config.scale
        bottom: 18 * Config.scale
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
            height: 64 * Config.scale
            border {
                top: 18 * Config.scale
                left: 18 * Config.scale
                right: 18 * Config.scale
                bottom: 18 * Config.scale
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

