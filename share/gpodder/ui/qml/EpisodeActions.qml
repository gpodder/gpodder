
import QtQuick 1.1

import 'config.js' as Config

Rectangle {
    id: episodeActions
    color: '#e0000000'

    property variant episode: undefined
    property bool playing: false

    height: Config.listItemHeight

    Row {
        anchors.centerIn: parent

        EpisodeActionItem {
            height: episodeActions.height
            text: _('Download')
            image: 'download'
            onSelected: controller.downloadEpisode(episode.episode)
            visible: (episode!==undefined)?(!episode.downloaded && !episode.downloading):false
        }

        EpisodeActionItem {
            height: episodeActions.height
            text: _('Cancel')
            image: 'download-cancel'
            onSelected: controller.cancelDownload(episode.episode)
            visible: (episode!==undefined)?(!episode.downloaded && episode.downloading):false
        }

        EpisodeActionItem {
            height: episodeActions.height
            text: (episode!==undefined)?(episodeActions.playing?_('Pause'):(episode.downloaded?_('Play'):_('Stream'))):''
            image: (episode!==undefined)?(episodeActions.playing?'pause':'play'):''
            onSelected: main.togglePlayback(episode.episode)
            visible: episode!==undefined
        }

        EpisodeActionItem {
            height: episodeActions.height
            text: _('Delete')
            image: 'delete'
            onSelected: controller.deleteEpisode(episode.episode)
            visible: (episode!==undefined)?(episode.downloaded && !episode.archive):false
        }

        EpisodeActionItem {
            height: episodeActions.height
            text: _('Shownotes')
            image: 'shownotes'
            onSelected: main.openShowNotes(episode.episode)
            visible: episode!==undefined
        }
    }
}

