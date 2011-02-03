
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

        delegate: PodcastItem {
            onPodcastSelected: rectangle.podcastSelected(podcast)
            onPodcastContextMenu: rectangle.podcastContextMenu(podcast)
        }

        header: Item { height: Config.headerHeight }
    }

}

