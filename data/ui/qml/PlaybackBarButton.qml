
import Qt 4.7

Image {
    signal clicked()

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        onClicked: parent.clicked()
    }

    Rectangle {
        anchors.fill: parent
        color: 'black'
        opacity: mouseArea.pressed?.2:0
    }
}

