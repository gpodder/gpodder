import QtQuick 1.1
import com.nokia.meego 1.0

import 'config.js' as Config
import 'util.js' as Util

SelectableItem {
    id: episodeItem
    property bool playing: false
    property real playbackPosition: playing?mediaPlayer.position:position
    property real playbackDuration: duration?duration:(playing?mediaPlayer.duration:0)

    height: Config.listItemHeight

    Rectangle {
        anchors {
            left: parent.left
            top: parent.top
            bottom: parent.bottom
        }

        visible: downloading || (playbackPosition && (episodeItem.playing || !episodeItem.inSelection))

        width: parent.width * (downloading?(progress):(playbackPosition / duration))
        color: downloading?Config.downloadColorBg:Config.playbackColorBg
    }

    Image {
        id: icon
        opacity: {
            if (downloaded) {
                1
            } else {
                .5
            }
        }
        source: {
            if (episodeModel.is_subset_view) {
                cover_url
            } else if (downloading) {
                'artwork/' + filetype + '-downloading.png'
            } else if (episodeItem.playing && true/*!episodeItem.inSelection*/) {
                'artwork/' + filetype + '-playing.png'
            } else {
                'artwork/' + filetype + '.png'
            }
        }

        sourceSize {
            width: Config.iconSize
            height: Config.iconSize
        }

        anchors {
            verticalCenter: parent.verticalCenter
            left: parent.left
            leftMargin: Config.largeSpacing
        }

        cache: true
    }

    Image {
        id: archiveIcon
        source: 'artwork/episode-archive.png'

        visible: modelData.qarchive

        sourceSize {
            width: Config.iconSize
            height: Config.iconSize
        }

        anchors {
            top: parent.top
            left: parent.left
            topMargin: Config.listItemHeight - height - Config.smallSpacing
        }
    }

    Column {
        anchors {
            left: icon.right
            leftMargin: Config.largeSpacing
            verticalCenter: parent.verticalCenter
        }

        Label {
            id: labelTitle

            text: title
            wrapMode: Text.NoWrap

            color: {
                if (downloading) {
                    Config.downloadColor
                } else if (episodeItem.playing) {
                    Config.playbackColor
                } else if (isnew && !downloaded) {
                    Config.newColor
                } else if (episodeItem.inSelection) {
                    Config.selectColor
                } else if (isnew && downloaded) {
                    'white'
                } else {
                    '#999'
                }
            }

            font.pixelSize: Config.listItemHeight * .35
        }

        Label {
            text: {
                if (episodeItem.playbackDuration && episodeItem.playbackPosition) {
                    Util.formatPosition(episodeItem.playbackPosition, episodeItem.playbackDuration)
                } else if (episodeItem.playbackDuration) {
                    Util.formatDuration(episodeItem.playbackDuration)
                } else {
                    ''
                }
            }
            font.pixelSize: Config.listItemHeight * .2
            color: labelTitle.color
        }
    }
}

