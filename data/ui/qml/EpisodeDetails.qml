
import Qt 4.7
import QtMultimediaKit 1.1

import "test"

import 'config.js' as Config

Item {
    id: episodeDetails

    property variant episode: undefined
    property alias playing: player.playing

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
        color: "white"

        Item {
            id: player
            property bool playing: audioPlayer.playing || videoPlayer.playing
            property bool seekLater: false
            property string fileType: (episode!=undefined)?episode.qfiletype:''
            property string source: (episode!=undefined)?episode.qsourceurl:''

            function start() {
                videoPlayer.source = ''
                audioPlayer.source = ''

                if (fileType == 'audio') {
                    audioPlayer.source = player.source
                    audioPlayer.play()
                } else if (fileType == 'video') {
                    videoPlayer.source = player.source
                    videoPlayer.play()
                } else {
                    console.log('Not an audio or video file!')
                    return
                }

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
                var playObj = (fileType=='video')?videoPlayer:audioPlayer
                playObj.position = position*episode.qduration*1000
            }
        }

        Video {
            id: videoPlayer
            opacity: (episode != undefined && episode.qfiletype == 'video')
            anchors.fill: parent

            onPositionChanged: player.positionChanged('video')
            onDurationChanged: player.durationChanged('video')
            onStatusChanged: player.statusChanged('video')
        }

        Audio {
            id: audioPlayer

            onPositionChanged: player.positionChanged('audio')
            onDurationChanged: player.durationChanged('audio')
            onStatusChanged: player.statusChanged('audio')
        }

        Flickable {
            id: showNotes

            visible: !videoPlayer.playing || (videoPlayer.opacity == 0)

            anchors.fill: parent
            contentHeight: showNotesText.height
            anchors.margins: Config.largeSpacing

            Text {
                id: showNotesText
                color: "black"
                font.pixelSize: 20
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                wrapMode: Text.Wrap
                text: episode!=undefined?('<h3 color="#666">'+episode.qtitle+'</h3>\n\n'+episode.qdescription):'No episode selected'
            }
        }

        PlaybackBar {
            progress: episode != undefined?(episode.qduration?(episode.qposition / episode.qduration):0):0
            onSetProgress: {
                player.setPosition(progress)
            }
            anchors {
                bottom: parent.bottom
                left: parent.left
                right: parent.right
            }
        }
    }
}

