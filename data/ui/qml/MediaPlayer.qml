
import Qt 4.7
import QtMultimediaKit 1.1

import 'config.js' as Config
import 'util.js' as Util

Item {
    id: mediaPlayer

    height: (Config.largeSpacing * 4) + (150 * Config.scale) + 110

    property variant episode: undefined

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
            }
        }

        function setPosition(position) {
            if (!playing) {
                playing = true
            }

            episode.qposition = position*episode.qduration
            audioPlayer.position = position*episode.qduration*1000
        }
    }

    function togglePlayback(episode) {
        if (mediaPlayer.episode == episode) {
            audioPlayer.paused = !audioPlayer.paused
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

            Text {
                id: episodeTitle
                text: episode.qtitle
                color: 'white'
                font.pixelSize: 30 * Config.scale
            }

            Text {
                id: podcastTitle
                text: episode.qpodcast.qtitle
                color: '#aaa'
                font.pixelSize: 20 * Config.scale
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

                        function seek(diff) {
                            if (episode != undefined && episode.qduration > 0) {
                                var pos = (episode.qposition + diff)/episode.qduration
                                if (pos < 0) pos = 0
                                audioPlayer.setPosition(pos)
                            }
                        }

                        onForward: seek(60)
                        onBackward: seek(-60)
                        onSlowForward: seek(10)
                        onSlowBackward: seek(-10)
                    }
                }

                Text {
                    anchors {
                        bottom: parent.bottom
                        right: parent.right
                    }
                    color: '#aaa'
                    text:  Util.formatDuration(episode.qposition) + ' / ' + Util.formatDuration(episode.qduration)
                    font.pixelSize: 15 * Config.scale
                }
            }

            PlaybackBarProgress {
                progress: episode != undefined?(episode.qduration?(episode.qposition / episode.qduration):0):0
                duration: episode != undefined?episode.qduration:0

                width: parent.width

                onSetProgress: {
                    audioPlayer.setPosition(progress)
                    audioPlayer.paused = false
                }
            }
        }
    }
}

