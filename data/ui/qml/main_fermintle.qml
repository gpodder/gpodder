
import Qt 4.7
import com.nokia.meego 1.0

PageStackWindow {
    id: rootWindow
    property variant main: mainObject

    initialPage: Page {
        id: mainPage

        Main {
            id: mainObject
            anchors.fill: parent
        }

    }

    Component.onCompleted: {
        theme.inverted = true
    }
}

