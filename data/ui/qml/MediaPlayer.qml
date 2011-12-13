
import Qt 4.7
import QtMultimediaKit 1.1
import com.nokia.meego 1.0

import 'config.js' as Config
import 'util.js' as Util

Item {
    id: mediaPlayer

    height: (Config.largeSpacing * 4) + (150 * Config.scale) + 110

    property variant episode: undefined
    property int startedFrom: 0

    onStartedFromChanged: {
        console.log('started from: ' + startedFrom)
    }

    function playedUntil(position) {
        console.log('played until: ' + parseInt(position))
        controller.storePlaybackAction(episode, startedFrom, position)
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
            episode.qposition = position/1000
        }

        onDurationChanged: {
            if (duration > 0) {
                episode.qduration = duration/1000
            }
        }

        onStatusChanged: {
            if (status == 6 && seekLater) {
                position = episode.qposition*1000
                seekLater = false
                mediaPlayer.startedFrom = position/1000
            } else if (status == 7) {
                mediaPlayer.playedUntil(audioPlayer.position/1000)
            }
        }

        function setPosition(position) {
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

    function togglePlayback(episode) {
        if (mediaPlayer.episode == episode) {
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
            controller.releaseEpisode(mediaPlayer.episode)
        }

        controller.acquireEpisode(episode)

        audioPlayer.paused = true
        mediaPlayer.episode = episode

        audioPlayer.stop()
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

                    source: (episode!==undefined)?Util.formatCoverURL(episode.qpodcast):''

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

