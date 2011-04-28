
import Qt 4.7
import com.meego 1.0

Window {
    id: window
    property variant main: mainObject

    PageStack {
        id: pageStack
        anchors.fill: parent

        Page {
            id: mainPage
            Main {
                id: mainObject
                anchors.fill: parent
            }

            Component.onCompleted: {
                pageStack.push(mainPage)
            }
        }
    }
}

