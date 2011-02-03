
import Qt 4.7

import 'config.js' as Config

Item {
    id: episodeList

    property alias model: listView.model
    property alias moving: listView.moving

    signal episodeSelected(variant episode)

    ListView {
        id: listView
        anchors.fill: parent
        model: episodeModel

        delegate: EpisodeItem {
            onEpisodeSelected: episodeList.episodeSelected(episode)
        }

        header: Item { height: Config.headerHeight }
    }
}

