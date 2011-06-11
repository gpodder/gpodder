
import Qt 4.7

TextInput {
    color: 'white'
    font.pixelSize: 20
    inputMethodHints: Qt.ImhNoAutoUppercase

    function closeVirtualKeyboard() {
        // noop on this platform
    }
}

