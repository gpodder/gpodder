
import Qt 4.7
import Qt.multimedia 1.0

Item {
    id: episodeDetails

    property variant episode
    property bool playing: audioPlayer.playing || videoPlayer.playing

    Rectangle {
        anchors.fill: parent
        opacity: .7
        color: "black"
    }

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

    ShadowText {
        id: episodeTitle

        visible: !videoPlayer.playing

        anchors.centerIn: parent
        color: "white"
        text: (episode != undefined)?episode.qtitle:''

        font.pixelSize: 20
    }

    Rectangle {
        id: progressBar
        height: 30
        color: "white"
        opacity: 0

        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom
        }

        Rectangle {
            color: "black"
            anchors {
                left: parent.left
                bottom: parent.bottom
                top: parent.top
            }
            width: (audioPlayer.duration > 0)?(parent.width*(audioPlayer.position/audioPlayer.duration)):(0)
        }

        ShadowText {
            anchors.centerIn: parent
            color: "white"
            text: ''+audioPlayer.position+'/'+audioPlayer.duration
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (audioPlayer.seekable) {
                    audioPlayer.position = audioPlayer.duration * mouse.x / width
                }
            }
        }
    }
}

