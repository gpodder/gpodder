
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
    property bool hasPlayButton: ((mediaPlayer.episode !== undefined)) && !progressIndicator.opacity
    property bool hasSearchButton: !progressIndicator.opacity

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
        pageStack.push(subscribePage);
    }

    function goBack() {
        mediaPlayer.stop()
        controller.quit()
    }

    function showFilterDialog() {
        episodeList.showFilterDialog()
    }

    function clickPlayButton() {
        if (!main.hasPlayButton) {
            main.showMessage(_('Playlist empty'));
            return;
        }

        if (pageStack.currentPage === mediaPlayerPage) {
            pageStack.pop();
        } else {
            pageStack.push(mediaPlayerPage);
        }
    }

    function showMultiEpisodesSheet(title, label, action) {
        multiEpisodesSheet.title = title;
        multiEpisodesSheet.acceptButtonText = label;
        multiEpisodesSheet.action = action;
        multiEpisodesList.selected = [];
        multiEpisodesList.contentY = episodeList.listViewContentY;
        multiEpisodesSheet.open();
        multiEpisodesSheet.opened = true;
    }

    width: 800
    height: 480

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

    PodcastList {
        id: podcastList

        anchors.fill: parent

        onPodcastSelected: {
            controller.podcastSelected(podcast);
            main.currentPodcast = podcast;
            pageStack.push(episodesPage);
        }
        onPodcastContextMenu: controller.podcastContextMenu(podcast)
        onSubscribe: pageStack.push(subscribePage);
    }

    Page {
        id: episodesPage

        EpisodeList {
            id: episodeList

            anchors.fill: parent

            model: ListModel { id: episodeListModel }
            onEpisodeContextMenu: controller.episodeContextMenu(episode)
        }

        tools: ToolBarLayout {
            ToolIcon {
                anchors.left: parent.left
                iconId: "icon-m-toolbar-back-white"
                onClicked: {
                    pageStack.pop();
                    episodeList.resetSelection();
                    main.currentPodcast = undefined;
                }
            }

            ToolButton {
                id: toolFilter
                width: 300
                onClicked: mainObject.showFilterDialog()
                anchors.centerIn: parent

                Label {
                    color: 'white'
                    text: mainObject.currentFilterText
                    anchors.centerIn: parent
                }
            }

            ToolIcon {
                onClicked: hrmtnEpisodesMenu.open()
                anchors.right: parent.right
                iconId: "toolbar-view-menu"
            }
        }

        ContextMenu {
            id: hrmtnEpisodesMenu

            MenuLayout {
                MenuItem {
                    id: nowPlayingMenuItem
                    text: _('Now playing')
                    onClicked: {
                        main.clickPlayButton();
                    }
                }
                MenuItem {
                    text: _('Download episodes')
                    onClicked: {
                        main.showMultiEpisodesSheet(text, _('Download'), 'download');
                    }
                }
                MenuItem {
                    text: _('Playback episodes')
                    onClicked: {
                        main.showMultiEpisodesSheet(text, _('Play'), 'play');
                    }
                }
                MenuItem {
                    text: _('Delete episodes')
                    onClicked: {
                        main.showMultiEpisodesSheet(text, _('Delete'), 'delete');
                    }
                }
            }
        }

    }

    Item {
        id: overlayInteractionBlockWall
        anchors.fill: parent
        z: 2

        opacity: (inputDialog.opacity || progressIndicator.opacity)?1:0
        Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (progressIndicator.opacity) {
                    // do nothing
                } else if (inputDialog.opacity) {
                    inputDialog.close()
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

    Page {
        id: mediaPlayerPage

        tools: ToolBarLayout {
            ToolIcon {
                anchors.left: parent.left
                iconId: "icon-m-toolbar-back-white"
                onClicked: {
                    pageStack.pop();
                    episodeList.resetSelection();
                    main.currentPodcast = undefined;
                }
            }

            ToolIcon {
                onClicked: mediaPlayerMenu.open()
                anchors.right: parent.right
                iconId: "toolbar-view-menu"
            }
        }

        MediaPlayer {
            id: mediaPlayer

            anchors {
                left: parent.left
                right: parent.right
                verticalCenter: parent.verticalCenter
            }
        }

        ContextMenu {
            id: mediaPlayerMenu

            MenuLayout {
                MenuItem {
                    text: _('Shownotes')
                    onClicked: main.openShowNotes(mediaPlayer.episode)
                }

                MenuItem {
                    text: _('Play queue')
                    onClicked: {
                        if (mediaPlayer.hasQueue) {
                            mediaPlayer.showQueue();
                        } else {
                            main.showMessage(_('Playlist empty'));
                        }
                    }
                }
            }
        }
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

    function showMessage(message) {
        infoBanner.text = message;
        infoBanner.show();
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

