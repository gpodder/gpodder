
import Qt 4.7

TextInput {
    // not used for now, but might be used in the future
    property string placeholderText: ''
    // the name of the action carried out when enter is pressed
    property string actionName: ''

    color: 'white'
    font.pixelSize: 20
    inputMethodHints: Qt.ImhNoAutoUppercase

    function closeVirtualKeyboard() {
        // noop on this platform
    }
}

