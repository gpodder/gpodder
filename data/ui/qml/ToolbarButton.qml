
import Qt 4.7

Item {
    property alias source: icon.source
    signal clicked

    height: parent.height
    width: parent.width / parent.children.length

    Image {
        id: icon
        anchors.centerIn: parent
    }

    Rectangle {
        id: highlight
        opacity: 0
        color: "white"
        anchors.fill: parent

        Behavior on opacity { NumberAnimation { duration: 100 } }
    }

    MouseArea {
        anchors.fill: parent
        onPressed: highlight.opacity = .3
        onReleased: highlight.opacity = 0
        onCanceled: highlight.opacity = 0
        onClicked: parent.clicked()
    }
}
