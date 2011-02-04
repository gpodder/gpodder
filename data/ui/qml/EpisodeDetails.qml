
import Qt 4.7
import Qt.multimedia 1.0

import 'config.js' as Config

Item {
    id: episodeDetails

    property variant episode
    property bool playing: audioPlayer.playing || videoPlayer.playing

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

