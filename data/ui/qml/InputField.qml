
import Qt 4.7
import com.nokia.meego 1.0

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

    platformSipAttributes: SipAttributes {
        actionKeyLabel: textField.actionName
        actionKeyHighlighted: true
        actionKeyEnabled: true
    }
}

