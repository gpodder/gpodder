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

    FilledIcon {
        id: icon
        source: 'artwork/' + modelData.qfiletype + '.png'
        width: Config.iconSize
        height: Config.iconSize
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Config.largeSpacing

        filled: modelData.qdownloaded?1:modelData.qprogress

        opacity: modelData.qdownloading?.5:1
        Behavior on opacity { PropertyAnimation { } }

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

