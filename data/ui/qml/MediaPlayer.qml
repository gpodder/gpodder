
import Qt 4.7
import QtMultimediaKit 1.1

import 'config.js' as Config
import 'util.js' as Util

Item {
    id: mediaPlayer

    height: (Config.largeSpacing * 2) + (150 * Config.scale)

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

        Row {
            spacing: Config.largeSpacing

            anchors {
                leftMargin: Config.largeSpacing
                topMargin: Config.largeSpacing
                left: parent.left
                top: parent.top
            }

            Image {
                id: coverArt
                source: (episode!==undefined)?Util.formatCoverURL(episode.qpodcast):''
                width: 150 * Config.scale
                height: 150 * Config.scale

                MouseArea {
                    anchors.fill: parent
                    onClicked: mediaPlayer.togglePlayback(episode)
                }

                sourceSize.width: width
                sourceSize.height: height
            }

            Column {
                id: textColumn

                spacing: Config.smallSpacing

                Item { height: 1; width: 1 }

                Text {
                    text: episode.qtitle
                    color: 'white'
                    font.pixelSize: 30 * Config.scale
                }

                Text {
                    text: episode.qpodcast.qtitle
                    color: '#aaa'
                    font.pixelSize: 20 * Config.scale
                }
            }
        }

        PlaybackBar {
            id: playbackBar

            width: mediaPlayer.width - coverArt.width - 3*Config.largeSpacing
            x: coverArt.width + 2*Config.largeSpacing

            anchors.bottom: parent.bottom
            anchors.bottomMargin: Config.largeSpacing

            Behavior on opacity { PropertyAnimation { } }

            progress: episode != undefined?(episode.qduration?(episode.qposition / episode.qduration):0):0
            duration: episode != undefined?episode.qduration:0

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
    }
}

