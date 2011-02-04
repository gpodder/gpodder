
import Qt 4.7

import 'config.js' as Config

Item {
    id: episodeList

    property alias model: listView.model
    property alias moving: listView.moving

    signal episodeSelected(variant episode)
    signal episodeContextMenu(variant episode)

    ListView {
        id: listView
        anchors.fill: parent
        model: episodeModel

        delegate: EpisodeItem {
            onSelected: episodeList.episodeSelected(item)
            onContextMenu: episodeList.episodeContextMenu(item)
        }

        header: Item { height: Config.headerHeight }
    }
}

