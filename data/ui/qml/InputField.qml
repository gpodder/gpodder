
import Qt 4.7
import com.nokia.meego 1.0

TextField {
    id: textField
    inputMethodHints: Qt.ImhNoAutoUppercase
    placeholderText: 'Search term or URL'
    signal accepted()

    Keys.onReturnPressed: accepted()
    Keys.onEnterPressed: accepted()

    function closeVirtualKeyboard() {
        textField.platformCloseSoftwareInputPanel()
    }
}

