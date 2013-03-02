
import QtQuick 1.1

import org.gpodder.qmlui 1.0

import 'config.js' as Config

SelectableItem {
    property string text: ''
    property string image: ''

    width: icon.width + Config.smallSpacing * 3 + text.width

    Image {
        id: icon
        source: parent.image?('artwork/episode-' + parent.image + '.png'):''
        height: Config.iconSize
        width: Config.iconSize

        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Config.smallSpacing
    }

    Label {
        id: text
        text: parent.text

        color: 'white'
        font.pixelSize: 20*Config.scale
        anchors.left: icon.right
        anchors.leftMargin: Config.smallSpacing
        anchors.verticalCenter: parent.verticalCenter
        anchors.rightMargin: Config.smallSpacing
    }
}

