import Qt 4.7

import 'config.js' as Config

Row {
    id: root
    property bool pressed: backward.pressed || forward.pressed || slowBackward.pressed || slowForward.pressed
    property string caption

    caption: {
        if (backward.pressed) {
            '- ' + controller.formatCount(n_('%(count)s minute', '%(count)s minutes', 1), 1)
        } else if (forward.pressed) {
            '+ ' + controller.formatCount(n_('%(count)s minute', '%(count)s minutes', 1), 1)
        } else if (slowBackward.pressed) {
            '- ' + controller.formatCount(n_('%(count)s second', '%(count)s seconds', 10), 10)
        } else if (slowForward.pressed) {
            '+ ' + controller.formatCount(n_('%(count)s second', '%(count)s seconds', 10), 10)
        } else {
            ''
        }
    }

    signal forward()
    signal backward()
    signal slowForward()
    signal slowBackward()

    height: 64 * Config.scale

    PlaybackBarButton {
        id: backward
        source: 'artwork/btn_fffwd.png'
        rotation: 180

        onClicked: root.backward()
    }

    PlaybackBarButton {
        id: slowBackward
        source: 'artwork/btn_ffwd.png'
        rotation: 180

        onClicked: root.slowBackward()
    }

    PlaybackBarButton {
        id: slowForward
        source: 'artwork/btn_ffwd.png'

        onClicked: root.slowForward()
    }

    PlaybackBarButton {
        id: forward
        source: 'artwork/btn_fffwd.png'

        onClicked: root.forward()
    }
}

