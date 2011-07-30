
import Qt 4.7

import 'config.js' as Config

SelectableItem {
    property alias text: buttonText.text
    property alias image: buttonImage.source
    signal clicked()

    property string modelData: ''
    width: 100
    height: Config.listItemHeight

    onSelected: clicked()

    Text {
        id: buttonText
        anchors.centerIn: parent
        color: 'white'
        font.pixelSize: 20
        font.bold: true
        text: ''
        visible: text != ''
    }

    ScaledIcon {
        id: buttonImage
        anchors.centerIn: parent
        visible: source != ''
    }
}

