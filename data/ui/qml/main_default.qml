
import Qt 4.7

Item {
    id: rootWindow
    property bool showStatusBar: true
    property variant main: mainObject

    width: 800
    height: 480

    Main {
        id: mainObject
        anchors.fill: parent
    }
}

