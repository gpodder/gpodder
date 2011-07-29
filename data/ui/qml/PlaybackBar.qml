import Qt 4.7

import 'config.js' as Config

Row {
    id: root
    signal forward()
    signal backward()
    signal slowForward()
    signal slowBackward()

    height: 64 * Config.scale

    PlaybackBarButton {
        source: 'artwork/btn_ffwd.png'
        rotation: 180

        onClicked: root.backward()
    }

    PlaybackBarButton {
        source: 'artwork/btn_ffwd.png'
        rotation: 180
        opacity: .5

        onClicked: root.slowBackward()
    }

    PlaybackBarButton {
        source: 'artwork/btn_ffwd.png'
        opacity: .5

        onClicked: root.slowForward()
    }

    PlaybackBarButton {
        source: 'artwork/btn_ffwd.png'

        onClicked: root.forward()
    }
}

