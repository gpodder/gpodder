
import QtQuick 1.1
import QtMultimediaKit 1.1
import com.nokia.meego 1.0

import 'config.js' as Config
import 'util.js' as Util

Item {
    id: mediaPlayer

    height: (Config.largeSpacing * 4) + (150 * Config.scale) + 110

    property variant episode: undefined
    property real position: audioPlayer.position/1000
    property real duration: audioPlayer.duration/1000
    property variant playQueue: []
    property int startedFrom: 0

    onStartedFromChanged: {
        console.log('started from: ' + startedFrom)
    }

    function playedUntil(position) {
        console.log('played until: ' + parseInt(position))
        controller.storePlaybackAction(episode, startedFrom, position)
    }

    function nextInQueue() {
        if (playQueue.length > 0) {
            var episode = playQueue[0];
            togglePlayback(episode);
            controller.releaseEpisode(episode);
            playQueue = playQueue.slice(1);
        }
    }

    Connections {
        target: mediaButtonsHandler

        onPlayPressed: togglePlayback(episode)
        onPausePressed: togglePlayback(episode)
        onPreviousPressed: playbackBar.backward()
        onNextPressed: playbackBar.forward()
    }

    property bool playing: audioPlayer.playing && !audioPlayer.paused

    onPlayingChanged: episode.qplaying = playing

    MouseArea {
        // clicks should not fall through!
        anchors.fill: parent
    }

    Audio {
        id: audioPlayer
        property bool seekLater: false

        onPositionChanged: {
            if (episode !== undefined) {
                episode.qposition = position/1000
            }
        }

        onDurationChanged: {
            if (duration > 0 && episode !== undefined) {
                episode.qduration = duration/1000
            }
        }

        onStatusChanged: {
            if (episode === undefined) {
                return;
            }

            if (status == 6 && seekLater) {
                position = episode.qposition*1000
                seekLater = false
                mediaPlayer.startedFrom = position/1000
            } else if (status == 7) {
                mediaPlayer.playedUntil(audioPlayer.position/1000)
                mediaPlayer.nextInQueue();
            }
        }

        function setPosition(position) {
            if (episode === undefined) {
                return;
            }

            if (!playing) {
                playing = true
            } else {
                mediaPlayer.playedUntil(audioPlayer.position/1000)
            }

            episode.qposition = position*episode.qduration
            audioPlayer.position = position*episode.qduration*1000
            mediaPlayer.startedFrom = audioPlayer.position/1000
        }
    }

    function enqueueEpisode(episode) {
        controller.acquireEpisode(episode);
        playQueue = playQueue.concat([episode]);
    }

    function removeQueuedEpisodesForPodcast(podcast) {
        var newQueue = [];

        for (var i in playQueue) {
            if (playQueue[i].qpodcast.equals(podcast)) {
                controller.releaseEpisode(playQueue[i]);
            } else {
                newQueue.push(playQueue[i]);
            }
        }

        playQueue = newQueue;
    }

    function removeQueuedEpisode(episode) {
        var newQueue = [];

        for (var i in playQueue) {
            if (playQueue[i].equals(episode)) {
                controller.releaseEpisode(playQueue[i]);
            } else {
                newQueue.push(playQueue[i]);
            }
        }

        playQueue = newQueue;
    }

    function togglePlayback(episode) {
        controller.currentEpisodeChanging();

        if (mediaPlayer.episode == episode && audioPlayer.status !== 7) {
            if (audioPlayer.paused) {
                mediaPlayer.startedFrom = audioPlayer.position/1000
            }
            audioPlayer.paused = !audioPlayer.paused
            if (audioPlayer.paused) {
                mediaPlayer.playedUntil(audioPlayer.position/1000)
            }
            return
        }

        if (mediaPlayer.episode !== undefined) {
            controller.releaseEpisode(mediaPlayer.episode);
        }

        audioPlayer.paused = true
        mediaPlayer.episode = episode
        audioPlayer.stop()

        if (episode === undefined) {
            nextInQueue();
            return;
        }

        controller.acquireEpisode(episode)

        audioPlayer.source = episode.qsourceurl
        audioPlayer.playing = true
        audioPlayer.paused = false

        if (episode.qposition && episode.qposition != episode.qduration) {
            audioPlayer.seekLater = true
        }
    }

    function stop() {
        audioPlayer.stop()
        audioPlayer.source = ''
    }

    Rectangle {
        id: mediaPlayerButtons
        color: 'black'
        anchors {
            top: mediaPlayerMain.bottom
            left: parent.left
            right: parent.right
        }

        Grid {
            columns: Util.isScreenPortrait() ? 1 : 2

            spacing: 2

            anchors.horizontalCenter: parent.horizontalCenter

            Button {
                id: showNotesButton
                width: parent.width * .9

                text: _('Shownotes')
                onClicked: {
                    nowPlayingThrobber.opened = false
                    main.openShowNotes(episode)
                }
            }

            Button {
                id: playQueueButton
                width: parent.width * .9

                visible: playQueue.length > 0

                text: _('Play queue') + ' (' + playQueue.length + ')'
                onClicked: playQueueDialog.showQueue();
            }
        }

        MultiSelectionDialog {
            id: playQueueDialog

            function showQueue() {
                selectedIndexes = [];
                model.clear();
                for (var index in playQueue) {
                    var episode = playQueue[index];
                    model.append({'name': episode.qtitle, 'position': index});
                }
                open();
            }

            onAccepted: {
                /**
                 * FIXME: If things have been removed from the play queue while
                 * the dialog was open, we have to subtract the values in
                 * selectedIndexes by the amount of played episodes to get the
                 * right episodes to delete. This is not yet done here.
                 * We can know from the nextInQueue() function (hint, hint)
                 **/
                var newQueue = [];
                for (var queueIndex in playQueue) {
                    var episode = playQueue[queueIndex];
                    var shouldRemove = false;

                    for (var index in selectedIndexes) {
                        var pos = model.get(selectedIndexes[index]).position;
                        if (queueIndex === pos) {
                            shouldRemove = true;
                            break;
                        }
                    }

                    if (shouldRemove) {
                        controller.releaseEpisode(episode);
                        /* Implicit removal by absence of newQueue.push() */
                    } else {
                        newQueue.push(episode);
                    }
                }
                playQueue = newQueue;
            }

            titleText: _('Play queue')
            acceptButtonText: _('Remove')
            model: ListModel { }
        }
    }

    Rectangle {
        id: mediaPlayerMain
        anchors.fill: mediaPlayer
        color: 'black'

        Column {
            spacing: Config.smallSpacing

            anchors {
                fill: parent
                margins: Config.largeSpacing
            }

            Label {
                id: episodeTitle
                text: (episode!=undefined)?episode.qtitle:''
                color: 'white'
                font.pixelSize: 30 * Config.scale
                elide: Text.ElideRight
                width: parent.width
            }

            Label {
                id: podcastTitle
                text: (episode!=undefined)?episode.qpodcast.qtitle:''
                color: '#aaa'
                font.pixelSize: 20 * Config.scale
                elide: Text.ElideRight
                width: parent.width
            }

            Item { height: 1; width: 1 }

            Row {
                spacing: Config.largeSpacing

                width: parent.width

                Image {
                    id: coverArt
                    width: 150 * Config.scale
                    height: 150 * Config.scale

                    source: (episode!==undefined)?episode.qpodcast.qcoverart:''

                    MouseArea {
                        anchors.fill: parent
                        onClicked: mediaPlayer.togglePlayback(episode)
                    }

                    Rectangle {
                        anchors.fill: parent
                        visible: audioPlayer.paused
                        color: '#dd000000'

                        ScaledIcon {
                            anchors.centerIn: parent
                            source: 'artwork/play.png'
                        }
                    }

                    sourceSize.width: width
                    sourceSize.height: height
                }

                Item {
                    height: coverArt.height
                    width: parent.width - coverArt.width - Config.largeSpacing

                    PlaybackBar {
                        id: playbackBar
                        anchors.centerIn: parent

                        Timer {
                            id: resetSeekButtonPressed
                            interval: 200
                            onTriggered: progressBar.seekButtonPressed = false
                        }

                        function seek(diff) {
                            if (episode != undefined && episode.qduration > 0) {
                                var pos = (episode.qposition + diff)/episode.qduration
                                if (pos < 0) pos = 0
                                audioPlayer.setPosition(pos)
                                progressBar.seekButtonPressed = true
                                progressBar.seekButtonPosition = (episode.qposition/episode.qduration)
                                resetSeekButtonPressed.restart()
                            }
                        }

                        onForward: seek(60)
                        onBackward: seek(-60)
                        onSlowForward: seek(10)
                        onSlowBackward: seek(-10)
                    }
                }

            }

            PlaybackBarProgress {
                id: progressBar

                overrideDisplay: playbackBar.pressed
                overrideCaption: playbackBar.caption

                isPlaying: mediaPlayer.playing
                progress: (episode != undefined)?(episode.qduration?(episode.qposition / episode.qduration):0):0
                duration: (episode != undefined)?episode.qduration:0

                width: parent.width

                onSetProgress: {
                    audioPlayer.setPosition(progress)
                    audioPlayer.paused = false
                }
            }
        }

        Label {
            anchors {
                bottom: parent.bottom
                right: parent.right
                bottomMargin: progressBar.height
                rightMargin: Config.largeSpacing
            }
            color: '#aaa'
            text: (episode!=undefined)?(Util.formatDuration(episode.qposition) + ' / ' + Util.formatDuration(episode.qduration)):'-'
            font.pixelSize: 15 * Config.scale
        }

    }
}

