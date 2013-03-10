
import QtQuick 1.1
import Sailfish.Silica 1.0

TextField {
    id: textField
    property string actionName: ''

    inputMethodHints: Qt.ImhNoAutoUppercase
    signal accepted()

    Keys.onReturnPressed: accepted()
    Keys.onEnterPressed: accepted()

    function closeVirtualKeyboard() {
        textField.platformCloseSoftwareInputPanel()
    }
}

