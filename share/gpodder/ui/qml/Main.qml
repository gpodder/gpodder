
import QtQuick 1.1
import com.nokia.meego 1.0

import 'config.js' as Config
import 'util.js' as Util

Item {
    id: main
    focus: true

    function _(x) {
        return controller.translate(x)
    }

    function n_(x, y, z) {
        return controller.ntranslate(x, y, z)
    }

    property alias podcastModel: podcastList.model
    property variant episodeModel
    property alias multiEpisodesSheetOpened: multiEpisodesSheet.opened
    onEpisodeModelChanged: episodeList.resetFilterDialog()
    property alias currentEpisode: mediaPlayer.episode
    property variant currentPodcast: undefined
    property bool hasPodcasts: podcastList.hasItems
    property alias currentFilterText: episodeList.currentFilterText

    property bool playing: mediaPlayer.playing
    property bool canGoBack: (main.state != 'podcasts' || contextMenu.state != 'closed' || mediaPlayer.visible) && !progressIndicator.opacity
    property bool hasPlayButton: ((contextMenu.state != 'opened') && (mediaPlayer.episode !== undefined)) && !progressIndicator.opacity
    property bool hasSearchButton: (contextMenu.state == 'closed' && main.state == 'podcasts') && !mediaPlayer.visible && !progressIndicator.opacity
    property bool hasFilterButton: state == 'episodes' && !mediaPlayer.visible

    property bool loadingEpisodes: false

    function clearEpisodeListModel() {
        loadingEpisodes = true
        startProgress(_('Loading episodes'))
    }

    function setEpisodeListModel(model) {
        episodeListModel.clear();
        for (var i=0; i<model.length; i++) {
            episodeListModel.append(model[i]);
        }
        loadingEpisodes = false
        endProgress()
    }

    function episodeUpdated(id) {
        for (var i=0; i<episodeListModel.count; i++) {
            var element = episodeListModel.get(i);
            if (element.episode_id === id) {
                var episode = element.episode;
                element.duration = episode.qduration;
                element.downloading = episode.qdownloading;
                element.position = episode.qposition;
                element.progress = episode.qprogress;
                element.downloaded = episode.qdownloaded;
                element.isnew = episode.qnew;
                element.archive = episode.qarchive;
                break;
            }
        }
    }

    function clickSearchButton() {
        contextMenu.showSubscribe()
    }

    function goBack() {
        if (mediaPlayer.visible) {
            clickPlayButton()
        } else if (contextMenu.state == 'opened') {
            contextMenu.state = 'closed'
        } else if (main.state == 'podcasts') {
            mediaPlayer.stop()
            controller.quit()
        } else if (main.state == 'episodes') {
            main.state = 'podcasts'
            main.currentPodcast = undefined
        }
    }

    function showFilterDialog() {
        episodeList.showFilterDialog()
    }

    function clickPlayButton() {
        mediaPlayer.visible = !mediaPlayer.visible;
    }

    function showMultiEpisodesSheet(title, label, action) {
        multiEpisodesSheet.title = title;
        multiEpisodesSheet.acceptButtonText = label;
        multiEpisodesSheet.action = action;
        multiEpisodesList.selected = [];
        multiEpisodesSheet.open();
        multiEpisodesSheet.opened = true;
    }

    width: 800
    height: 480

    state: 'podcasts'

    function enqueueEpisode(episode) {
        if (currentEpisode === undefined) {
            togglePlayback(episode);
        } else {
            mediaPlayer.enqueueEpisode(episode);
        }
    }

    function removeQueuedEpisodesForPodcast(podcast) {
        mediaPlayer.removeQueuedEpisodesForPodcast(podcast);
    }

    function removeQueuedEpisode(episode) {
        mediaPlayer.removeQueuedEpisode(episode);
    }

    function togglePlayback(episode) {
        if (episode !== undefined) {
            if (episode.qfiletype == 'video') {
                controller.playVideo(episode);
            } else {
                mediaPlayer.togglePlayback(episode);
            }
            controller.onPlayback(episode);
        }
    }

    function openShowNotes(episode) {
        showNotes.episode = episode;
        pageStack.push(showNotesPage);
    }

    function openContextMenu(items) {
        hrmtnContextMenu.items = items
        hrmtnContextMenu.open()
    }

    function startProgress(text) {
        progressIndicator.text = text
        progressIndicator.opacity = 1
    }

    function endProgress() {
        progressIndicator.opacity = 0
    }

    states: [
        State {
            name: 'podcasts'
            PropertyChanges {
                target: podcastList
                opacity: 1
            }
            PropertyChanges {
                target: episodeList
                anchors.leftMargin: 100
                opacity: 0
            }
            StateChangeScript {
                script: episodeList.resetSelection()
            }
        },
        State {
            name: 'episodes'
            PropertyChanges {
                target: episodeList
                opacity: !main.loadingEpisodes
            }
            PropertyChanges {
                target: podcastList
                opacity: 0
                anchors.leftMargin: -100
            }
        }
    ]

    Item {
        id: listContainer
        anchors.fill: parent

        PodcastList {
            id: podcastList
            opacity: 0

            anchors.fill: parent

            onPodcastSelected: {
                controller.podcastSelected(podcast)
                main.currentPodcast = podcast
            }
            onPodcastContextMenu: controller.podcastContextMenu(podcast)
            onSubscribe: contextMenu.showSubscribe()

            Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
            Behavior on anchors.leftMargin { NumberAnimation { duration: Config.slowTransition } }
        }

        EpisodeList {
            id: episodeList
            mainState: main.state

            model: ListModel { id: episodeListModel }

            opacity: 0

            anchors.fill: parent

            onEpisodeContextMenu: controller.episodeContextMenu(episode)

            Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
            Behavior on anchors.leftMargin { NumberAnimation { duration: Config.slowTransition } }
        }

        Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
        Behavior on scale { NumberAnimation { duration: Config.fadeTransition } }
    }

    Item {
        id: overlayInteractionBlockWall
        anchors.fill: parent
        z: (contextMenu.state != 'opened')?2:0

        opacity: (mediaPlayer.visible || contextMenu.state == 'opened' || messageDialog.opacity || inputDialog.opacity || progressIndicator.opacity)?1:0
        Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (contextMenu.state == 'opened') {
                    // do nothing
                } else if (progressIndicator.opacity) {
                    // do nothing
                } else if (inputDialog.opacity) {
                    inputDialog.close()
                } else if (messageDialog.opacity) {
                    messageDialog.opacity = 0
                } else {
                    mediaPlayer.visible = false
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            color: 'black'
            opacity: .7
        }

        Image {
            anchors.fill: parent
            source: 'artwork/mask.png'
        }
    }

    MediaPlayer {
        id: mediaPlayer
        visible: false

        z: 3

        anchors.top: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: visible?-(height+(parent.height-height)/2):0

        Behavior on anchors.topMargin { PropertyAnimation { duration: Config.quickTransition; easing.type: Easing.OutCirc } }
    }

    ContextMenu {
        id: hrmtnContextMenu
        property variant items: []

        MenuLayout {
            Repeater {
                model: hrmtnContextMenu.items

                MenuItem {
                    text: modelData.caption
                    onClicked: {
                        hrmtnContextMenu.close()
                        controller.contextMenuResponse(index)
                    }
                }
            }
        }
    }

    ContextMenuArea {
        id: contextMenu

        width: parent.width
        opacity: 0

        anchors {
            top: parent.top
            bottom: parent.bottom
        }

        onClose: contextMenu.state = 'closed'
        onResponse: controller.contextMenuResponse(index)

        state: 'closed'

        Behavior on opacity { NumberAnimation { duration: Config.fadeTransition } }

        states: [
            State {
                name: 'opened'
                PropertyChanges {
                    target: contextMenu
                    opacity: 1
                }
                AnchorChanges {
                    target: contextMenu
                    anchors.right: main.right
                }
            },
            State {
                name: 'closed'
                PropertyChanges {
                    target: contextMenu
                    opacity: 0
                }
                AnchorChanges {
                    target: contextMenu
                    anchors.right: main.left
                }
                StateChangeScript {
                    script: controller.contextMenuClosed()
                }
            }
        ]

        transitions: Transition {
            AnchorAnimation { duration: Config.slowTransition }
        }
    }

    function showMessage(message) {
        messageDialogText.text = message
        messageDialog.opacity = 1
    }

    Item {
        id: messageDialog
        anchors.fill: parent
        opacity: 0
        z: 20

        Behavior on opacity { PropertyAnimation { } }

        Label {
            id: messageDialogText
            anchors {
                left: parent.left
                right: parent.right
                verticalCenter: parent.verticalCenter
                leftMargin: Config.largeSpacing
                rightMargin: Config.largeSpacing
            }
            color: 'white'
            font.pixelSize: 20
            font.bold: true
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
    }

    function showInputDialog(message, value, accept, reject, textInput) {
        inputDialogText.text = message
        inputDialogField.text = value
        inputDialogAccept.text = accept
        inputDialogReject.text = reject
        inputDialogField.visible = textInput

        if (textInput) {
            inputSheet.open()
        } else {
            queryDialog.open()
        }
    }

    QueryDialog {
        id: queryDialog

        acceptButtonText: inputDialogAccept.text
        rejectButtonText: inputDialogReject.text

        message: inputDialogText.text

        onAccepted: inputDialog.accept()
        onRejected: inputDialog.close()
    }

    Sheet {
        id: multiEpisodesSheet
        property string action: 'delete'
        property bool opened: false
        property string title: ''
        acceptButtonText: _('Delete')
        visualParent: episodeList
        anchors.fill: parent
        anchors.topMargin: -36

        rejectButtonText: _('Cancel')

        onAccepted: {
            controller.multiEpisodeAction(multiEpisodesList.selected, action);
            multiEpisodesSheet.opened = false;
        }

        onRejected: {
            multiEpisodesSheet.opened = false;
        }

        content: Item {
            anchors.fill: parent
            ListView {
                id: multiEpisodesList
                property variant selected: []

                anchors.fill: parent
                model: episodeList.model

                delegate: EpisodeItem {
                    property variant modelData: episode
                    inSelection: multiEpisodesList.selected.indexOf(index) !== -1
                    onSelected: {
                        var newSelection = [];
                        var found = false;

                        for (var i=0; i<multiEpisodesList.selected.length; i++) {
                            var value = multiEpisodesList.selected[i];
                            if (value === index) {
                                found = true;
                            } else {
                                newSelection.push(value);
                            }
                        }

                        if (!found) {
                            if (multiEpisodesSheet.action === 'delete' && item.qarchive) {
                                // cannot delete archived episodes
                            } else {
                                newSelection.push(index);
                            }
                        }

                        multiEpisodesList.selected = newSelection;
                    }

                    onContextMenu: multiEpisodesSheetContextMenu.open();
                }
            }

            ScrollDecorator { flickableItem: multiEpisodesList }

            ContextMenu {
                id: multiEpisodesSheetContextMenu

                MenuLayout {
                    MenuItem {
                        text: _('Select all')
                        onClicked: {
                            var newSelection = [];
                            for (var i=0; i<multiEpisodesList.count; i++) {
                                newSelection.push(i);
                            }
                            multiEpisodesList.selected = newSelection;
                        }
                    }

                    MenuItem {
                        text: _('Select downloaded')
                        onClicked: {
                            var newSelection = [];
                            for (var i=0; i<multiEpisodesList.count; i++) {
                                if (main.episodeModel.get_object_by_index(i).downloaded) {
                                    newSelection.push(i);
                                }
                            }
                            multiEpisodesList.selected = newSelection;
                        }
                    }

                    MenuItem {
                        text: _('Select none')
                        onClicked: {
                            multiEpisodesList.selected = [];
                        }
                    }

                    MenuItem {
                        text: _('Invert selection')
                        onClicked: {
                            var newSelection = [];
                            for (var i=0; i<multiEpisodesList.count; i++) {
                                if (multiEpisodesList.selected.indexOf(i) === -1) {
                                    newSelection.push(i);
                                }
                            }
                            multiEpisodesList.selected = newSelection;
                        }
                    }
                }
            }
        }
    }

    Sheet {
        id: inputSheet

        acceptButtonText: inputDialogAccept.text
        rejectButtonText: inputDialogReject.text

        content: Item {
            anchors.fill: parent

            MouseArea {
                anchors.fill: parent
                onClicked: console.log('caught')
            }

            Column {
                anchors.fill: parent
                anchors.margins: Config.smallSpacing
                spacing: Config.smallSpacing

                Item {
                    height: 1
                    width: parent.width
                }

                Label {
                    id: inputDialogText
                    anchors.margins: Config.smallSpacing
                    width: parent.width
                }

                Item {
                    height: 1
                    width: parent.width
                }

                InputField {
                    id: inputDialogField
                    width: parent.width
                    onAccepted: {
                        inputDialog.accept()
                        inputSheet.close()
                    }
                    actionName: inputDialogAccept.text
                }
            }
        }

        onAccepted: inputDialog.accept()
        onRejected: inputDialog.close()
    }

    Item {
        id: inputDialog
        anchors.fill: parent
        opacity: 0

        function accept() {
            opacity = 0
            scale = .5
            controller.inputDialogResponse(true, inputDialogField.text,
                                           inputDialogField.visible)
        }

        function close() {
            opacity = 0
            scale = .5
            controller.inputDialogResponse(false, inputDialogField.text,
                                           inputDialogField.visible)
        }

        SimpleButton {
            id: inputDialogReject
            width: parent.width / 2
            onClicked: inputDialog.close()
        }

        SimpleButton {
            id: inputDialogAccept
            width: parent.width / 2
            onClicked: inputDialog.accept()
        }
    }

    Column {
        id: progressIndicator
        property string text: '...'
        anchors.centerIn: parent
        opacity: 0
        spacing: Config.largeSpacing * 2
        z: 40

        Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }

        Label {
            text: parent.text
            anchors.horizontalCenter: parent.horizontalCenter
        }

        BusyIndicator {
            anchors.horizontalCenter: parent.horizontalCenter
            running: parent.opacity > 0
        }
    }
}

