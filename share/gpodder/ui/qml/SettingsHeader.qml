
import QtQuick 1.0

import 'config.js' as Config

Item {
    id: settingsHeader
    property alias text: headerCaption.text
    property color color: Config.settingsHeaderColor

    width: parent.width
    height: headerCaption.visible?Config.listItemHeight*.7:10

    Rectangle {
        id: horizontalLine

        anchors {
            left: parent.left
            right: headerCaption.left
            rightMargin: headerCaption.visible?Config.smallSpacing:0
            verticalCenter: headerCaption.verticalCenter
        }

        height: 1
        color: settingsHeader.color
    }

    Text {
        id: headerCaption
        text: ''
        visible: text !== ''
        color: settingsHeader.color
        font.pixelSize: 17

        anchors {
            right: parent.right
            bottom: parent.bottom
        }
    }
}

