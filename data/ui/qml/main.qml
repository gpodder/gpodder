
import Qt 4.7

Item {
    state: 'podcasts'

    function setCurrentEpisode(episode) {
        episodeDetails.episode = episode
    }

    states: [
        State {
            name: 'podcasts'
            PropertyChanges {
                target: podcastList
                opacity: 1
            }
        },
        State {
            name: 'episodes'
            PropertyChanges {
                target: episodeList
                opacity: 1
            }
        },
        State {
            name: 'player'
            PropertyChanges {
                target: episodeDetails
                opacity: 1
            }
            StateChangeScript {
                script: episodeDetails.startPlayback()
            }
        }
    ]

    PodcastList {
        id: podcastList
        model: podcastModel
        opacity: 0

        anchors.fill: parent

        onPodcastSelected: controller.podcastSelected(podcast)
        onPodcastContextMenu: controller.podcastContextMenu(podcast)
        onAction: controller.action(action)

        Behavior on opacity { NumberAnimation { duration: 500 } }
    }

    EpisodeList {
        id: episodeList
        model: episodeModel
        opacity: 0

        anchors.fill: parent

        title: uidata.episodeListTitle
        onGoBack: parent.state = 'podcasts'
        onEpisodeSelected: controller.episodeSelected(episode)

        Behavior on opacity { NumberAnimation { duration: 500 } }
    }

    EpisodeDetails {
        id: episodeDetails
        opacity: 0

        anchors.fill: parent
        onGoBack: parent.state = 'episodes'

        Behavior on opacity { NumberAnimation { duration: 500 } }
    }
}
