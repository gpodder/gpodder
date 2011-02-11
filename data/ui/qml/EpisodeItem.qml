import Qt 4.7

import 'config.js' as Config

SelectableItem {
    id: episodeItem

    height: Config.listItemHeight

    Rectangle {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        width: modelData.qduration?(parent.width * (modelData.qposition / modelData.qduration)):0
        height: Config.smallSpacing
        color: 'white'
        opacity: .3
    }

    Image {
        id: icon
        source: 'episodeList/' + modelData.qfiletype + '.png'
        width: Config.iconSize
        height: Config.iconSize
        opacity: modelData.qdownloaded?1:.1
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Config.largeSpacing
    }

    ShadowText {
        text: modelData.qtitle
        color: modelData.qnew?"white":"#888"
        font.pixelSize: episodeItem.height * .35
        font.bold: false
        anchors.left: icon.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: positionInfo.left
        anchors.leftMargin: Config.largeSpacing
        anchors.rightMargin: Config.smallSpacing
        clip: true
    }

    ShadowText {
        id: positionInfo
        text: modelData.qpositiontext
        color: '#888'
        anchors.right: parent.right
        anchors.rightMargin: Config.largeSpacing
        anchors.verticalCenter: parent.verticalCenter
    }
}

