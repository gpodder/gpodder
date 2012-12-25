
import QtQuick 1.1

import com.nokia.meego 1.0

import 'config.js' as Config
import 'util.js' as Util

SelectableItem {
    id: podcastItem

    Image {
        id: cover

        source: modelData.qcoverart
        asynchronous: true
        width: podcastItem.height * .8
        height: width
        sourceSize.width: width
        sourceSize.height: height

        anchors {
            verticalCenter: parent.verticalCenter
            left: parent.left
            leftMargin: Config.smallSpacing
            rightMargin: Config.smallSpacing
        }
    }

    Label {
        id: titleBox

        text: modelData.qtitle
        color: (counters.newEpisodes > 0)?Config.newColor:"white"

        anchors {
            verticalCenter: parent.verticalCenter
            left: cover.visible?cover.right:cover.left
            leftMargin: Config.smallSpacing
            rightMargin: Config.smallSpacing
        }

        font.pixelSize: podcastItem.height * .35
        elide: Text.ElideRight
        wrapMode: Text.NoWrap
    }

    Item {
        id: counterBox
        width: Config.iconSize * 1.3

        anchors {
            left: titleBox.right
            right: parent.right
            top: parent.top
            bottom: parent.bottom
            rightMargin: Config.smallSpacing
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
            right: parent.right
            rightMargin: Config.smallSpacing
        }
        visible: modelData.qupdating
        running: visible
    }
}

