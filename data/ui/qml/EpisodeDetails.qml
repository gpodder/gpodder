
import Qt 4.7
import Qt.multimedia 1.0

Rectangle {
    id: episodeDetails

    property variant episode
    signal goBack

    color: "red"

    function startPlayback() {
        if (episode.qfiletype == 'video') {
            videoPlayer.play()
        } else {
            audioPlayer.play()
        }
    }

    Video {
        id: videoPlayer
        opacity: (episode.qfiletype == 'video')?(1):(0)
        anchors.fill: parent
        source: episode.qurl
    }

    Audio {
        id: audioPlayer
        source: episode.qurl
    }

    Text {
        color: "white"
        text: episode.qtitle + ' ' + audioPlayer.position
    }

    MouseArea {
        anchors.fill: parent
        onClicked: episodeDetails.goBack()
    }
}

