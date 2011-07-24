
import Qt 4.7

import 'config.js' as Config

Item {
    id: episodeActions

    property variant episode: undefined
    //color: 'black'
    //source: 'artwork/episode-background.png'
    //fillMode: Image.TileHorizontally

    height: Config.listItemHeight

    Row {
        anchors.centerIn: parent

        EpisodeActionItem {
            height: episodeActions.height
            text: 'Download'
            image: 'download'
            onSelected: controller.downloadEpisode(episode)
            visible: (episode!==undefined)?(!episode.qdownloaded && !episode.qdownloading):false
        }

        EpisodeActionItem {
            height: episodeActions.height
            text: 'Cancel'
            image: 'download-cancel'
            onSelected: controller.cancelDownload(episode)
            visible: (episode!==undefined)?(!episode.qdownloaded && episode.qdownloading):false
        }

        EpisodeActionItem {
            height: episodeActions.height
            text: 'Delete'
            image: 'delete'
            onSelected: controller.deleteEpisode(episode)
            visible: (episode!==undefined)?(episode.qdownloaded && !episode.qarchive):false
        }

        EpisodeActionItem {
            height: episodeActions.height
            text: (episode!==undefined)?(episode.qplaying?'Pause':'Play'):''
            image: (episode!==undefined)?(episode.qplaying?'pause':'play'):''
            visible: episode!==undefined
        }

        EpisodeActionItem {
            height: episodeActions.height
            text: 'Shownotes'
            image: 'shownotes'
            onSelected: episodeList.episodeSelected(episode)
            visible: episode!==undefined
        }
    }
}

