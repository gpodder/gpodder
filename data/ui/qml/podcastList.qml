
import Qt 4.7

Rectangle {
    id: rectangle
    height: 400

    ListView {
        anchors.fill: parent

        delegate: Rectangle {
            height: 20
            width: parent.width
            color: "blue"

            Text {
                text: model.podcast.qtitle
                anchors.fill: parent
            }
        }

        model: podcastModel
    }
}

