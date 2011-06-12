
import Qt 4.7
import QtMultimediaKit 1.1

import "test"

import 'config.js' as Config

Item {
    id: episodeDetails

    property variant episode: undefined
    property bool playing: player.playing && !player.paused
    property bool fullscreen: false

    MouseArea {
        // clicks should not fall through!
        anchors.fill: parent
    }

    function startPlayback() {
        player.start()
    }

    function stop() {
        player.stop()
    }

    Rectangle {
        anchors.fill: episodeDetails
        color: videoPlayer.visible?"black":"white"

        Behavior on color { ColorAnimation { } }

        Item {
            id: player
            property bool paused: false
            property bool playing: audioPlayer.playing || videoPlayer.playing
            property bool seekLater: false
            property string fileType: (episode!=undefined)?episode.qfiletype:''
            property string source: (episode!=undefined)?episode.qsourceurl:''

            function start() {
                videoPlayer.source = ''
                audioPlayer.source = ''

                if (fileType == 'audio') {
                    audioPlayer.source = player.source
                    audioPlayer.playing = true
                } else if (fileType == 'video') {
                    videoPlayer.source = player.source
                    videoPlayer.playing = true
                } else {
                    console.log('Not an audio or video file!')
                    return
                }

                player.paused = true

                if (episode.qposition && episode.qposition != episode.qduration) {
                    player.seekLater = true
                }
            }

            function stop() {
                audioPlayer.source = ''
                videoPlayer.source = ''
                audioPlayer.stop()
                videoPlayer.stop()
            }

            function positionChanged(typ) {
                if (typ != fileType) return;
                var playObj = (typ=='video')?videoPlayer:audioPlayer
                episode.qposition = playObj.position/1000
            }

            function durationChanged(typ) {
                if (typ != fileType) return;
                var playObj = (typ=='video')?videoPlayer:audioPlayer

                if (playObj.duration > 0) {
                    episode.qduration = playObj.duration/1000
                }
            }

            function statusChanged(typ) {
                if (typ != fileType) return;
                var playObj = (typ=='video')?videoPlayer:audioPlayer

                if (playObj.status == 6 && seekLater) {
                    playObj.position = episode.qposition*1000
                    seekLater = false
                }
            }

            function setPosition(position) {
                var playObj = undefined

                if (fileType == 'video') {
                    playObj = videoPlayer
                } else if (fileType == 'audio') {
                    playObj = audioPlayer
                } else {
                    return
                }

                if (!playObj.playing) {
                    playObj.playing = true
                }

                playObj.position = position*episode.qduration*1000
            }
        }

        Video {
            id: videoPlayer
            paused: player.paused || player.fileType != 'video'
            visible: (episode != undefined && episode.qfiletype == 'video')
            anchors.fill: parent

            onPlayingChanged: {
                if (!playing) {
                    playing = true
                    position = 0
                    player.paused = true
                }
            }

            onPausedChanged: {
                if (player.fileType == 'video') {
                    episode.qplaying = !paused
                }
            }

            onPositionChanged: player.positionChanged('video')
            onDurationChanged: player.durationChanged('video')
            onStatusChanged: player.statusChanged('video')

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    episodeDetails.fullscreen = !episodeDetails.fullscreen
                    rootWindow.showStatusBar = !episodeDetails.fullscreen
                }
            }
        }

        Audio {
            id: audioPlayer
            paused: player.paused || player.fileType != 'audio'

            onPlayingChanged: {
                if (!playing) {
                    playing = true
                    position = 0
                    player.paused = true
                }
            }

            onPausedChanged: {
                if (player.fileType == 'audio') {
                    episode.qplaying = !paused
                }
            }

            onPositionChanged: player.positionChanged('audio')
            onDurationChanged: player.durationChanged('audio')
            onStatusChanged: player.statusChanged('audio')
        }

        Flickable {
            id: showNotes

            visible: !videoPlayer.visible

            anchors.fill: parent
            contentHeight: showNotesText.height
            anchors.margins: Config.largeSpacing

            Text {
                id: showNotesText
                color: "black"
                font.pixelSize: 20 * Config.scale
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                wrapMode: Text.Wrap
                text: episode!=undefined?('<h3 color="#666">'+episode.qtitle+'</h3>\n\n'+episode.qdescription):'No episode selected'
            }
        }

        PlaybackBar {
            id: playbackBar

            opacity: episodeDetails.fullscreen?0:1

            Behavior on opacity { PropertyAnimation { } }

            visible: (player.fileType == 'audio') || (player.fileType == 'video')
            progress: episode != undefined?(episode.qduration?(episode.qposition / episode.qduration):0):0
            duration: episode != undefined?episode.qduration:0
            paused: player.paused
            onSetProgress: {
                player.setPosition(progress)
                player.paused = false
            }
            onForward: {
                if (episode != undefined && episode.qduration > 0) {
                    var pos = (episode.qposition + 60)/episode.qduration
                    player.setPosition(pos)
                }
            }
            onBackward: {
                if (episode != undefined && episode.qduration > 0) {
                    var pos = (episode.qposition - 60)/episode.qduration
                    if (pos < 0) pos = 0
                    player.setPosition(pos)
                }
            }
            onSetPaused: {
                player.paused = !player.paused
            }
            anchors {
                bottom: parent.bottom
                left: parent.left
                right: parent.right
                bottomMargin: Config.largeSpacing * 2
                leftMargin: Config.largeSpacing * 2
                rightMargin: Config.largeSpacing * 2
            }
        }
    }
}

