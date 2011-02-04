import Qt 4.7

import 'config.js' as Config

SelectableItem {
    id: episodeItem

    height: Config.listItemHeight

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
        font.pointSize: episodeItem.height * .25
        font.bold: false
        anchors.left: icon.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.leftMargin: Config.largeSpacing
    }
}

