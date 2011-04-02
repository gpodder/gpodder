import Qt 4.7

import 'config.js' as Config

Item {
    id: root
    property real progress: 0
    property bool paused: false
    property int duration: 0
    signal setProgress(real progress)
    signal setPaused()
    signal forward()
    signal backward()

    height: 64

    Rectangle {
        radius: Config.smallSpacing
        anchors.fill: parent
        color: 'black'
        opacity: .8
    }

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

        state: root.paused?'play':'pause'

        onClicked: root.setPaused()
    }

    PlaybackBarButton {
        id: rwnd
        anchors.left: play.right
        source: 'artwork/btn_ffwd.png'
        rotation: 180

        onClicked: root.backward()
    }

    PlaybackBarProgress {
        anchors.left: rwnd.right
        anchors.right: ffwd.left

        onSetProgress: root.setProgress(progress)

        progress: root.progress
        duration: root.duration
    }

    PlaybackBarButton {
        id: ffwd
        anchors.right: parent.right
        source: 'artwork/btn_ffwd.png'

        onClicked: root.forward()
    }

}
