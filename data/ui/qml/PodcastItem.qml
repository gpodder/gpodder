
import Qt 4.7

Image {
    signal podcastSelected(variant podcast)
    signal podcastContextMenu(variant podcast)

    id: podcastItem
    source: 'podcastList/bg.png'
    width: parent.width

    Rectangle {
        id: highlight
        opacity: 0
        color: "white"
        anchors.fill: parent

        Behavior on opacity { NumberAnimation { duration: 200 } }
    }

    Image {
    	id: cover
        source: 'podcastList/cover-shadow.png'

        anchors {
            verticalCenter: parent.verticalCenter
            left: parent.left
            leftMargin: 10
        }

        Image {
            source: model.podcast.qcoverfile
            sourceSize.width: width
            sourceSize.height: height
            width: parent.width - 12
            height: parent.height - 12
            anchors.centerIn: parent
        }
    }

    Column {
        id: titleBox

        anchors {
            verticalCenter: parent.verticalCenter
            left: cover.right
            leftMargin: 10
            right: counter.left
            rightMargin: 10
        }

        ShadowText {
            id: titleText
            text: model.podcast.qtitle
            elide: Text.ElideRight
            color: "white"
            anchors {
                left: parent.left
                right: parent.right
            }
            font.pixelSize: 22
        }

        ShadowText {
            id: descriptionText
            text: model.podcast.qdescription
            visible: text != ''
            elide: Text.ElideRight
            color: "#aaa"
            offsetX: -1
            offsetY: -1
            anchors {
                left: parent.left
                right: parent.right
            }
            font.pixelSize: 18
        }
    }

    Image {
        id: counter
        source: 'podcastList/count.png'
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: counterText.left
        anchors.leftMargin: -10
        visible: counterText.text != ''
    }

    Text {
        id: counterText
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: 5
        text: (model.podcast.qdownloaded)?(''+model.podcast.qdownloaded):('')
        color: "white"
        font.pixelSize: counter.height * 3 / 4
    }

    MouseArea {
        anchors.fill: parent
        onPressed: highlight.opacity = .2
        onClicked: parent.podcastSelected(model.podcast)
        onReleased: highlight.opacity = 0
        onCanceled: highlight.opacity = 0
        onPressAndHold: parent.podcastContextMenu(model.podcast)
    }
}

