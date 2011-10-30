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
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width * modelData.qprogress
        height: modelData.qdownloading?parent.height:0
        color: '#608ae234'
        opacity: modelData.qdownloaded?0:.3
        Behavior on opacity { PropertyAnimation { } }
        Behavior on height { PropertyAnimation { } }
    }

    Rectangle {
        id: playbackProgress

        anchors.left: parent.left

        anchors.verticalCenter: parent.verticalCenter
        width: modelData.qduration?(parent.width * (modelData.qposition / modelData.qduration)):0
        height: parent.height
        color: '#60729fcf'
        opacity: .3
    }

    Image {
        id: icon
        source: 'artwork/' + modelData.qfiletype + (modelData.qdownloading?'-downloading':(modelData.qplaying?'-playing':'')) + '.png'
        width: Config.iconSize
        height: Config.iconSize
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Config.largeSpacing
        opacity: (modelData.qdownloaded || modelData.qdownloading)?1:.3
        Behavior on opacity { PropertyAnimation { } }
    }

    Label {
        id: title
        text: modelData.qtitle
        wrapMode: Text.NoWrap
        color: modelData.qdownloading?'#8ae234':(modelData.qplaying?'#729fcf':(modelData.qnew?"white":"#888"))
        font.pixelSize: episodeItem.height * .35
        font.bold: false
        anchors.left: icon.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: positionInfo.left
        anchors.leftMargin: Config.largeSpacing
        anchors.rightMargin: Config.smallSpacing
        clip: true
    }

    Label {
        id: positionInfo
        text: Util.formatDuration(modelData.qduration)
        font.pixelSize: episodeItem.height * .2
        color: '#888'
        anchors.right: archiveIcon.visible?archiveIcon.left:parent.right
        anchors.rightMargin: Config.largeSpacing
        anchors.verticalCenter: parent.verticalCenter
    }

    Image {
        id: archiveIcon
        source: 'artwork/episode-archive.png'
        opacity: .5
        visible: modelData.qarchive
        width: Config.iconSize
        height: Config.iconSize
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.rightMargin: Config.largeSpacing
    }
}

