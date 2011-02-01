
import Qt 4.7

Image {
    default property alias children: buttonRow.children

    source: 'podcastList/toolbar.png'
    width: parent.width

    Row {
        id: buttonRow
        anchors.fill: parent
    }
}
