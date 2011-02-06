
import Qt 4.7
import QtMultimediaKit 1.1

import "test"

import 'config.js' as Config

Item {
    id: episodeDetails

    property variant episode: Episode {}
    property bool playing: audioPlayer.playing || videoPlayer.playing
    property bool seekLater: false

    MouseArea {
        // clicks should not fall through!
        anchors.fill: parent
    }

    function startPlayback() {
        if (episode.qfiletype == 'video') {
            audioPlayer.stop()
            videoPlayer.play()
        } else {
            videoPlayer.stop()
            audioPlayer.play()
            console.log('starting playback, seekable=' + audioPlayer.seekable
                        + ' and pos=' + episode.qposition*1000)
            episodeDetails.seekLater = true
        }
    }

    function stop() {
        audioPlayer.source = ''
        videoPlayer.source = ''
        audioPlayer.stop()
        videoPlayer.stop()
    }

    Rectangle {
        anchors.fill: episodeDetails
        color: "white"

        Video {
            id: videoPlayer
            opacity: (episode != undefined && episode.qfiletype == 'video')?(1):(0)
            anchors.fill: parent
            source: (episode != undefined)?episode.qsourceurl:''
        }

        Audio {
            id: audioPlayer
            source: (episode != undefined)?episode.qsourceurl:''
            onPositionChanged: {
                episode.qposition = audioPlayer.position/1000
            }
            onDurationChanged: {
                if (audioPlayer.duration > 0) {
                    episode.qduration = audioPlayer.duration/1000
                }
            }
            onStatusChanged: {
                console.log('status changed:' + audioPlayer.status)
                if (audioPlayer.status == 6 && episodeDetails.seekLater) {
                    console.log('seeking now (status changed)')
                    audioPlayer.position = episode.qposition*1000
                    episodeDetails.seekLater = false
                }
            }
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
                text: (episode != undefined)?('<h3 color="#666">'+episode.qtitle+'</h3>\n\n'+episode.qdescription):''
            }
        }
    }
}

