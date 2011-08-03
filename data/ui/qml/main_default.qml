
import Qt 4.7

Item {
    id: rootWindow
    property bool showStatusBar: true
    property variant main: mainObject

    width: 480
    height: 854

    Main {
        id: mainObject
        anchors.fill: parent
    }
}

