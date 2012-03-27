
import Qt 4.7

import 'config.js' as Config

Item {
    id: episodeActions

    property variant episode: undefined

    height: Config.listItemHeight

    Row {
        anchors.centerIn: parent

        EpisodeActionItem {
            height: episodeActions.height
            text: _('Download')
            image: 'download'
            onSelected: controller.downloadEpisode(episode)
            visible: (episode!==undefined)?(!episode.qdownloaded && !episode.qdownloading):false
        }

        EpisodeActionItem {
            height: episodeActions.height
            text: _('Cancel')
            image: 'download-cancel'
            onSelected: controller.cancelDownload(episode)
            visible: (episode!==undefined)?(!episode.qdownloaded && episode.qdownloading):false
        }

        EpisodeActionItem {
            height: episodeActions.height
            text: (episode!==undefined)?(episode.qplaying?_('Pause'):(episode.qdownloaded?_('Play'):_('Stream'))):''
            image: (episode!==undefined)?(episode.qplaying?'pause':'play'):''
            onSelected: main.togglePlayback(episode)
            visible: episode!==undefined
        }

        EpisodeActionItem {
            height: episodeActions.height
            text: _('Delete')
            image: 'delete'
            onSelected: controller.deleteEpisode(episode)
            visible: (episode!==undefined)?(episode.qdownloaded && !episode.qarchive):false
        }

        EpisodeActionItem {
            height: episodeActions.height
            text: _('Shownotes')
            image: 'shownotes'
            onSelected: main.openShowNotes(episode)
            visible: episode!==undefined
        }
    }
}

