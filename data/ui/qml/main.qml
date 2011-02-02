
import Qt 4.7

Item {

    function showEpisodes() {
        podcastList.opacity = 0
        episodeList.opacity = 1
    }

    function showPodcasts() {
        podcastList.opacity = 1
        episodeList.opacity = 0
    }

    PodcastList {
        id: podcastList
        model: podcastModel
        opacity: 1

        anchors.fill: parent

        onPodcastSelected: { /*FIXME UGLY*/ episodeList.title = podcast.qtitle; controller.podcastSelected(podcast) }
        onPodcastContextMenu: controller.podcastContextMenu(podcast)
        onAction: controller.action(action)

        Behavior on opacity { NumberAnimation { duration: 500 } }
    }

    EpisodeList {
        id: episodeList
        model: episodeModel
        opacity: 0

        anchors.fill: parent

        onGoBack: parent.showPodcasts()

        Behavior on opacity { NumberAnimation { duration: 500 } }
    }
}
