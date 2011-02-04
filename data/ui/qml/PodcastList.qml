
import Qt 4.7

import 'config.js' as Config

Item {
    property alias moving: listView.moving

    signal podcastSelected(variant podcast)
    signal podcastContextMenu(variant podcast)
    signal action(string action)

    id: rectangle

    property alias model: listView.model

    ListView {
        id: listView
        anchors.fill: parent

        section.property: 'section'
        section.delegate: Item {
            height: Config.headerHeight
            ShadowText {
                font.pixelSize: parent.height * .5
                text: section
                color: "#aaa"
                anchors {
                    //bottomMargin: Config.smallSpacing
                    leftMargin: Config.switcherWidth / 3
                    bottom: parent.bottom
                    left: parent.left
                    right: parent.right
                }
            }
        }

        delegate: PodcastItem {
            onSelected: rectangle.podcastSelected(item)
            onContextMenu: rectangle.podcastContextMenu(item)
        }

        header: Item { height: Config.headerHeight }
    }

}

