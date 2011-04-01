
import Qt 4.7

Item {
    property variant main
    property list<Action> actions
    property string episodeListTitle: 'Episodes'

    actions: [
        Action { caption: 'Download' },
        Action { caption: 'Upload' },
        Action { caption: 'Sideload' },
        Action { caption: 'Reload' }
    ]

    function titleChanged(text) {
        console.log('title changed:' + text)
    }

    function podcastSelected(podcast) {
        episodeListTitle = podcast.qtitle
        main.state = 'episodes'
    }

    function podcastContextMenu(podcast) {
        console.log('Context menu for podcast')
        main.openContextMenu(actions)
    }

    function contextMenuResponse(index) {
        console.log('Context menu response')
    }

    function contextMenuClosed() {
        console.log('Context menu closed')
    }

    function episodeSelected(episode) {
        console.log('Episode selected')
        main.setCurrentEpisode(episode)
    }

    function episodeContextMenu(episode) {
        console.log('Episode context menu')
        main.openContextMenu(actions)
    }

    function searchButtonClicked() {
        main.openContextMenu(actions)
    }

    function quit() {
        Qt.quit()
    }

    function switcher() {
        console.log('Task switcher activated')
    }

    function loadLastEpisode() {
        console.log('Load last episode')
    }
}

