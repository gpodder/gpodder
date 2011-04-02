import Qt 4.7

Item {
    id: root
    property real progress: 0
    signal setProgress(real progress)

    height: 64

    Rectangle { anchors.fill: parent ; color: 'black'; opacity: .7 }

    PlaybackBarButton {
        id: play
        source: 'artwork/btn_play.png'
        anchors.left: parent.left

        states: [
            State {
                name: 'play'
                PropertyChanges {
                    target: play
                    source: 'artwork/btn_play.png'
                }
            },
            State {
                name: 'pause'
                PropertyChanges {
                    target: play
                    source: 'artwork/btn_pause.png'
                }
            }
        ]

        state: 'play'

        onClicked: {
            if (state == 'play') {
                state = 'pause'
            } else {
                state = 'play'
            }
        }
    }

    PlaybackBarButton {
        id: rwnd
        anchors.left: play.right
        source: 'artwork/btn_ffwd.png'
        rotation: 180
    }

    PlaybackBarProgress {
        anchors.left: rwnd.right
        anchors.right: ffwd.left
        progress: root.progress
        onSetProgress: root.setProgress(progress)
    }

    PlaybackBarButton {
        id: ffwd
        anchors.right: parent.right
        source: 'artwork/btn_ffwd.png'
    }

}
