
import Qt 4.7
import QtMultimediaKit 1.1

import "test"

import 'config.js' as Config

Item {
    id: episodeDetails

    property variant episode: Episode {}
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
            property string fileType: episode.qfiletype

            function start() {
                if (fileType == 'audio') {
                    videoPlayer.stop()
                    audioPlayer.play()
                } else {
                    audioPlayer.stop()
                    videoPlayer.play()
                }
                player.seekLater = true
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
        }

        Video {
            id: videoPlayer
            opacity: (episode.qfiletype == 'video')
            anchors.fill: parent
            source: episode.qsourceurl

            onPositionChanged: player.positionChanged('video')
            onDurationChanged: player.durationChanged('video')
            onStatusChanged: player.statusChanged('video')
        }

        Audio {
            id: audioPlayer
            source: episode.qsourceurl

            onPositionChanged: player.positionChanged('audio')
            onDurationChanged: player.durationChanged('audio')
            onStatusChanged: player.statusChanged('audio')
        }

        Flickable {
            id: showNotes

            visible: !videoPlayer.playing

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
                text: '<h3 color="#666">'+episode.qtitle+'</h3>\n\n'+episode.qdescription
            }
        }
    }
}

