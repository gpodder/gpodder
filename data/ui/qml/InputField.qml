
import Qt 4.7
import com.nokia.meego 1.0

TextField {
    id: textField
    inputMethodHints: Qt.ImhNoAutoUppercase

    function closeVirtualKeyboard() {
        textField.platformCloseSoftwareInputPanel()
    }
}

