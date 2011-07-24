
import Qt 4.7

import 'config.js' as Config

Item {
    id: podcastList

    property alias model: listView.model
    property alias moving: listView.moving

    signal podcastSelected(variant podcast)
    signal podcastContextMenu(variant podcast)

    ListView {
        id: listView
        anchors.fill: parent

        section.property: 'section'
        section.delegate: Item {
            height: Config.headerHeight
            Text {
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
            onSelected: podcastList.podcastSelected(item)
            onContextMenu: podcastList.podcastContextMenu(item)
        }

        header: PodcastListHeader { }
        footer: Item { height: Config.headerHeight }
    }

}

