
import Qt 4.7

import 'config.js' as Config

Item {
    id: contextMenu

    property variant items: ['context menu']

    signal close
    signal response(int index)

    MouseArea {
        anchors.fill: parent
        onClicked: contextMenu.close()
    }

    Rectangle {
        color: "black"
        anchors.fill: parent
        opacity: .9
    }

    ListView {

        model: contextMenu.items
        anchors.fill: parent

        header: Item { height: Config.headerHeight * 2 }

        delegate: Item {
            height: Config.listItemHeight
            anchors.left: parent.left
            anchors.right: parent.right

            Rectangle {
                anchors.fill: parent
                color: "white"
                opacity: (rowMouseArea.pressed)?.3:0
            }

            ShadowText {
                anchors.leftMargin: Config.switcherWidth
                anchors {
                    left: parent.left
                    right: parent.right
                    verticalCenter: parent.verticalCenter
                }
                color: "white"
                font.pixelSize: parent.height * .3
                text: modelData
            }

            MouseArea {
                id: rowMouseArea
                anchors.fill: parent
                onClicked: {
                    contextMenu.response(index)
                    contextMenu.close()
                }
            }
        }
    }
}

