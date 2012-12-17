import Qt 4.7
import com.nokia.meego 1.0

import 'config.js' as Config
import 'util.js' as Util

SelectableItem {
    id: episodeItem

    // Show context menu when single-touching the icon
    singlePressContextMenuLeftBorder: title.x

    height: Config.listItemHeight

    Rectangle {
        id: downloadProgress

        anchors {
            left: parent.left
            top: parent.top
            bottom: parent.bottom
        }

        visible: modelData.qdownloading
        width: parent.width * modelData.qprogress
        color: Config.downloadColorBg
    }

    Rectangle {
        id: playbackProgress

        anchors {
            left: parent.left
            top: parent.top
            bottom: parent.bottom
        }

        visible: modelData.qduration && !(downloadProgress.visible && downloadProgress.width > 0)
        width: parent.width * (modelData.qposition / modelData.qduration)
        color: Config.playbackColorBg
    }

    Image {
        id: icon
        source: {
            if (episodeModel.is_subset_view) {
                Util.formatCoverURL(modelData.qpodcast)
            } else {
                'artwork/' + modelData.qfiletype + (modelData.qdownloading?'-downloading':(modelData.qplaying?'-playing':'')) + '.png'
            }
        }
        sourceSize.width: width
        sourceSize.height: height

        width: Config.iconSize
        height: Config.iconSize
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Config.largeSpacing
        opacity: modelData.qdownloaded?1:.3
        Behavior on opacity { PropertyAnimation { } }

        cache: true
    }

    Label {
        id: title
        text: modelData.qtitle
        wrapMode: Text.NoWrap
        color: modelData.qdownloading?Config.downloadColor:(modelData.qplaying?Config.playbackColor:(modelData.qnew?(modelData.qdownloaded?"white":Config.newColor):'#ddd'))
        font.pixelSize: episodeItem.height * .35

        anchors.left: icon.right
        anchors.leftMargin: Config.largeSpacing

        anchors.top: parent.top
        anchors.topMargin: Config.smallSpacing * 1.5
    }

    Label {
        id: positionInfo
        text: modelData.qduration?Util.formatDuration(modelData.qduration):''
        font.pixelSize: episodeItem.height * .2
        color: '#888'

        anchors.left: icon.right
        anchors.leftMargin: Config.largeSpacing

        anchors.bottom: parent.bottom
        anchors.bottomMargin: Config.smallSpacing * 1.5
    }

    Image {
        id: archiveIcon
        source: 'artwork/episode-archive.png'
        opacity: .5
        visible: modelData.qarchive
        width: Config.iconSize
        height: Config.iconSize

        anchors.left: parent.left
        //anchors.leftMargin: Config.smallSpacing

        anchors.bottom: parent.bottom
        anchors.bottomMargin: Config.smallSpacing

        cache: true
    }
}

