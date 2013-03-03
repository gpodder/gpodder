
import QtQuick 1.1

import org.gpodder.qmlui 1.0

import 'config.js' as Config
import 'util.js' as Util

SelectableItem {
    id: podcastItem

    Item {
        id: counterBox
        width: Config.iconSize * 1.3

        anchors {
            left: parent.left
            top: parent.top
            bottom: parent.bottom
        }

        Label {
            id: counters

            property int newEpisodes: modelData.qnew
            property int downloadedEpisodes: modelData.qdownloaded

            anchors {
                verticalCenter: parent.verticalCenter
                right: parent.right
                rightMargin: 3
            }

            visible: !spinner.visible && (downloadedEpisodes > 0)
            text: counters.downloadedEpisodes
            color: "white"

            font.pixelSize: podcastItem.height * .4
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

        source: modelData.qcoverart
        asynchronous: true
        width: podcastItem.height * .8
        height: width
        sourceSize.width: width
        sourceSize.height: height
        clip: true

        anchors {
            verticalCenter: parent.verticalCenter
            left: counterBox.right
            leftMargin: Config.smallSpacing
        }

        Rectangle {
            anchors {
                horizontalCenter: parent.right
                verticalCenter: parent.bottom
            }
            opacity: .5
            color: Config.newColor
            visible: counters.newEpisodes > 0
            width: parent.width * .6
            height: width
            rotation: 45
        }
    }

    Label {
        id: titleBox

        text: modelData.qtitle
        color: 'white'

        anchors {
            verticalCenter: parent.verticalCenter
            left: cover.visible?cover.right:cover.left
            leftMargin: Config.smallSpacing
            right: parent.right
            rightMargin: Config.smallSpacing
        }

        font.pixelSize: podcastItem.height * .35
        wrapMode: Text.NoWrap
    }
}

