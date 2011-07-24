
import Qt 4.7
import QtMultimediaKit 1.1

import 'config.js' as Config

Item {
    id: mediaPlayer

    property variant episode: undefined

    property bool playing: audioPlayer.playing && !audioPlayer.paused

    onPlayingChanged: episode.qplaying = playing

    MouseArea {
        // clicks should not fall through!
        anchors.fill: parent
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

        Audio {
            id: audioPlayer
            property bool seekLater: false

            /*onPlayingChanged: {
                if (!playing) {
                    playing = true
                    position = 0
                    paused = true
                }
            }*/

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

        PlaybackBar {
            id: playbackBar

            Behavior on opacity { PropertyAnimation { } }

            progress: episode != undefined?(episode.qduration?(episode.qposition / episode.qduration):0):0
            duration: episode != undefined?episode.qduration:0
            paused: audioPlayer.paused
            onSetProgress: {
                audioPlayer.setPosition(progress)
                audioPlayer.paused = false
            }
            onForward: {
                if (episode != undefined && episode.qduration > 0) {
                    var pos = (episode.qposition + 60)/episode.qduration
                    audioPlayer.setPosition(pos)
                }
            }
            onBackward: {
                if (episode != undefined && episode.qduration > 0) {
                    var pos = (episode.qposition - 60)/episode.qduration
                    if (pos < 0) pos = 0
                    audioPlayer.setPosition(pos)
                }
            }
            onSetPaused: {
                audioPlayer.paused = !audioPlayer.paused
            }
            anchors {
                bottom: parent.bottom
                left: parent.left
                right: parent.right
                bottomMargin: Config.largeSpacing
                leftMargin: Config.largeSpacing * 2
                rightMargin: Config.largeSpacing * 2
            }
        }
    }
}

