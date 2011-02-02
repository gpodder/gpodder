
import Qt 4.7
import Qt.multimedia 1.0

Rectangle {
    id: episodeDetails
    signal goBack

    property variant episode
    property bool playing: audioPlayer.playing || videoPlayer.playing

    color: "black"

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
        opacity: (episode.qfiletype == 'video')?(1):(0)
        anchors.fill: parent
        source: episode.qsourceurl
    }

    Audio {
        id: audioPlayer
        source: episode.qsourceurl
    }

    ShadowText {
        id: episodeTitle

        visible: !videoPlayer.playing

        anchors {
            verticalCenter: parent.verticalCenter
            left: parent.left
            right: parent.right
            leftMargin: 20
            rightMargin: 20
        }
        elide: Text.ElideEnd
        color: "white"
        text: episode.qtitle
        font.pixelSize: 20
    }

    MouseArea {
        anchors.fill: parent
        onClicked: episodeDetails.goBack()
    }

    Rectangle {
        id: progressBar
        height: 30
        color: "white"

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

