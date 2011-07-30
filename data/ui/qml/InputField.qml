
import Qt 4.7

TextInput {
    // not used for now, but might be used in the future
    property string placeholderText: ''

    color: 'white'
    font.pixelSize: 20
    inputMethodHints: Qt.ImhNoAutoUppercase

    function closeVirtualKeyboard() {
        // noop on this platform
    }
}

