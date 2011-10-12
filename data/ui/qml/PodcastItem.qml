
import Qt 4.7

import com.nokia.meego 1.0

import 'config.js' as Config
import 'util.js' as Util

SelectableItem {
    id: podcastItem

    // Show context menu when single-touching the count or cover art
    singlePressContextMenuLeftBorder: titleBox.x

    Item {
        id: counterBox
        width: Config.iconSize * 1.9

        anchors {
            left: parent.left
            top: parent.top
            bottom: parent.bottom
        }

        Column {
            id: counters
            visible: !spinner.visible

            property int newEpisodes: modelData.qnew
            property int downloadedEpisodes: modelData.qdownloaded

            anchors {
                verticalCenter: parent.verticalCenter
                right: parent.right
                rightMargin: 5
            }

            Label {
                anchors.right: parent.right

                visible: counters.downloadedEpisodes > 0
                text: counters.downloadedEpisodes
                color: "white"

                font.pixelSize: podcastItem.height * .4
            }

            Label {
                anchors.right: parent.right

                visible: counters.newEpisodes > 0
                text: '+' + counters.newEpisodes
                color: 'yellow'

                font.pixelSize: podcastItem.height * .3
            }
        }
    }

    BusyIndicator {
        id: spinner
        anchors {
            verticalCenter: parent.verticalCenter
            right: cover.left
            rightMargin: Config.smallSpacing
        }
        visible: modelData.qupdating
        running: visible
    }

    Image {
    	id: cover

        visible: modelData.qcoverurl != ''
        source: Util.formatCoverURL(modelData)
        asynchronous: true
        width: podcastItem.height * .8
        height: width
        sourceSize.width: width
        sourceSize.height: height

        anchors {
            verticalCenter: parent.verticalCenter
            left: counterBox.right
            leftMargin: Config.smallSpacing
        }
    }

    Label {
        id: titleBox

        text: modelData.qtitle
        color: "white"

        anchors {
            verticalCenter: parent.verticalCenter
            left: cover.visible?cover.right:cover.left
            leftMargin: Config.smallSpacing
            right: parent.right
            rightMargin: Config.smallSpacing
        }

        font.pixelSize: podcastItem.height * .35
        elide: Text.ElideRight
        wrapMode: Text.NoWrap
    }
}

