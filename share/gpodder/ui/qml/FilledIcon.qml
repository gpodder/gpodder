
import QtQuick 1.1

Item {
    id: filledIcon
    property alias source: bg.source
    property real filled: 1

    Image {
        id: bg
        anchors.fill: parent
        opacity: .1
    }

    Item {
        Image {
            id: fg
            source: bg.source
            width: bg.width
            height: bg.height
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
        }
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        clip: true
        height: parent.height * filledIcon.filled
    }
}

