
import Qt 4.7

Rectangle {
    id: episodeList
    property alias model: listView.model
    property alias title: headerText.text
    signal goBack
    color: 'white'

    Image {
        anchors.fill: parent
        source: 'podcastList/mask.png'
        sourceSize { height: 100; width: 100 }
    }

    Image {
        anchors.fill: parent
        source: 'podcastList/noise.png'
    }

    ListView {
        id: listView
        anchors.topMargin: header.height
        anchors.fill: parent
        model: episodeModel
        delegate: EpisodeItem {}
    }

    Image {
        id: header
        width: parent.width
        source: 'episodeList/header.png'
        ShadowText {
            id: headerText
            anchors {
                verticalCenter: parent.verticalCenter
                left: parent.left
                right: parent.right
                leftMargin: 20
            }
            text: "Episodes"
            font.pixelSize: 30
            color: "white"
        }

        Item {
            id: backButton
            width: backButtonImage.sourceSize.width + 40
            height: parent.height
            
            anchors {
                verticalCenter: parent.verticalCenter
                right: parent.right
            }

            Rectangle {
                id: backButtonHighlight
                color: "white"
                opacity: (backButtonMouseArea.pressed)?(.5):(0)
                anchors.fill: parent
                Behavior on opacity { NumberAnimation { duration: 500 } }
            }

            Image {
                id: backButtonImage
                anchors.centerIn: parent
                source: 'episodeList/back.png'
            }

            MouseArea {
                id: backButtonMouseArea
                anchors.fill: parent
                onClicked: episodeList.goBack()
            }
        }
    }
}

