
import Qt 4.7

import 'config.js' as Config

Item {
    id: contextMenuArea

    property variant items: []

    signal close
    signal response(int index)

    MouseArea {
        anchors.fill: parent
    }

    Rectangle {
        color: "black"
        anchors.fill: parent
        opacity: .9
    }

    ListView {
        model: contextMenuArea.items
        anchors.fill: parent

        header: Item { height: Config.headerHeight * 2 }
        footer: Item { height: Config.headerHeight }

        delegate: SelectableItem {
            ShadowText {
                anchors.leftMargin: Config.switcherWidth
                anchors {
                    left: parent.left
                    right: parent.right
                    verticalCenter: parent.verticalCenter
                }
                color: "white"
                font.pixelSize: parent.height * .3
                text: modelData.caption
            }

            onSelected: {
                contextMenuArea.response(index)
                contextMenuArea.close()
            }
        }
    }
}

