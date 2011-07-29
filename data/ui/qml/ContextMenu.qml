
import Qt 4.7

import 'config.js' as Config

Item {
    id: contextMenuArea

    property bool subscribeMode: true

    property variant items: []

    signal close
    signal response(int index)

    ListView {
        id: listView
        visible: !contextMenuArea.subscribeMode
        model: contextMenuArea.items
        anchors.fill: parent

        header: Item { height: Config.headerHeight * 2 }
        footer: Item { height: Config.headerHeight }

        delegate: SelectableItem {
            Text {
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

    function showSubscribe() {
        contextMenuArea.subscribeMode = true
        contextMenuArea.state = 'opened'
        subscribe.show()
    }

    Subscribe {
        id: subscribe
        visible: contextMenuArea.subscribeMode && (contextMenuArea.state == 'opened')
        anchors.fill: parent
        anchors.topMargin: Config.headerHeight

        onSubscribe: {
            controller.addSubscription(url)
            contextMenuArea.close()
        }
    }
}

