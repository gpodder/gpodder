
import Qt 4.7

Rectangle {
    state: 'podcasts'
    color: 'black'

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
            StateChangeScript {
                script: episodeDetails.lastState = 'podcasts'
            }
        },
        State {
            name: 'episodes'
            PropertyChanges {
                target: episodeList
                opacity: 1
            }
            StateChangeScript {
                script: episodeDetails.lastState = 'episodes'
            }
        },
        State {
            name: 'player'
            PropertyChanges {
                target: episodeDetails
                anchors.topMargin: 0
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
        property string lastState: 'episodes'

        id: episodeDetails
        opacity: (parent.state == 'player' || y > -height)?1:0
        clip: y != 0

        height: parent.height

        anchors {
            topMargin: -height
            top: parent.top
            left: parent.left
            right: parent.right
        }
        onGoBack: parent.state = lastState 

        Behavior on anchors.topMargin { NumberAnimation { duration: 200 } }
    }

    NowPlayingThrobber {
        property bool shouldAppear: (episodeDetails.playing && !podcastList.moving)

        id: nowPlayingThrobber
        anchors.top: episodeDetails.bottom
        anchors.right: parent.right
        anchors.rightMargin: 100
        opacity: shouldAppear?1:0

        onClicked: parent.state = 'player'

        Behavior on opacity { NumberAnimation { duration: 100 } }
    }
}


