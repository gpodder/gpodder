
import Qt 4.7

Image {
    default property alias children: buttonColumn.children

    source: 'podcastList/toolbar_landscape.png'
    height: parent.height

    Column {
        id: buttonColumn
        anchors.fill: parent
    }
}
